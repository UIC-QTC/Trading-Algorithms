#This program is in the classic algorithm style and was taken from QuantConnect's community 
from itertools import groupby
from datetime import datetime, timedelta
from pytz import utc
UTCMIN = datetime.min.replace(tzinfo=utc)

import numpy as np
import pandas as pd
from scipy.optimize import minimize

class CustomOptimizationPortfolioConstructionModel(PortfolioConstructionModel):
    
    '''
    Description:
        Allocate optimal weights to each security in order to optimize the portfolio objective function provided
    Details:
        - The target percent holdings of each security is 1/N where N is the number of securities with active Up/Down insights
        - For InsightDirection.Up, long targets are returned
        - For InsightDirection.Down, short targets are returned
        - For InsightDirection.Flat, closing position targets are returned
    '''

    def __init__(self, objectiveFunction = 'std', rebalancingParam = False):
        
        '''
        Description:
            Initialize a new instance of CustomOptimizationPortfolioConstructionModel
        Args:
            objectiveFunction: The function to optimize. If set to 'equal', it will just perform equal weighting
            rebalancingParam: Integer indicating the number of days for rebalancing (default set to False, no rebalance)
                - Independent of this parameter, the portfolio will be rebalanced when a security is added/removed/changed direction
        '''
        
        if objectiveFunction != 'equal':
            # minWeight set to 0 to ensure long only weights
            self.optimizer = CustomPortfolioOptimizer(minWeight = 0, maxWeight = 1, objFunction = objectiveFunction) # initialize the optimizer
        
        self.optWeights = None
        self.objectiveFunction = objectiveFunction
        self.insightCollection = InsightCollection()
        self.removedSymbols = []
        self.nextExpiryTime = UTCMIN
        self.rebalancingTime = UTCMIN
        
        # if the rebalancing parameter is not False but a positive integer
        # convert rebalancingParam to timedelta and create rebalancingFunc
        if rebalancingParam > 0:
            self.rebalancing = True
            rebalancingParam = timedelta(days = rebalancingParam)
            self.rebalancingFunc = lambda dt: dt + rebalancingParam
        else:
            self.rebalancing = rebalancingParam

    def CreateTargets(self, algorithm, insights):

        '''
        Description:
            Create portfolio targets from the specified insights
        Args:
            algorithm: The algorithm instance
            insights: The insights to create portfolio targets from
        Returns:
            An enumerable of portfolio targets to be sent to the execution model
        '''

        targets = []
        
        # check if we have new insights coming from the alpha model or if some existing insights have expired
        # or if we have removed symbols from the universe
        if (len(insights) == 0 and algorithm.UtcTime <= self.nextExpiryTime and self.removedSymbols is None):
            return targets
        
        # here we get the new insights and add them to our insight collection
        for insight in insights:
            self.insightCollection.Add(insight)
            
        # create flatten target for each security that was removed from the universe
        if self.removedSymbols is not None:
            universeDeselectionTargets = [ PortfolioTarget(symbol, 0) for symbol in self.removedSymbols ]
            targets.extend(universeDeselectionTargets)
            self.removedSymbols = None

        # get insight that haven't expired of each symbol that is still in the universe
        activeInsights = self.insightCollection.GetActiveInsights(algorithm.UtcTime)

        # get the last generated active insight for each symbol
        lastActiveInsights = []
        for symbol, g in groupby(activeInsights, lambda x: x.Symbol):
            lastActiveInsights.append(sorted(g, key = lambda x: x.GeneratedTimeUtc)[-1])

        # check if we actually want to create new targets for the securities (check function ShouldCreateTargets for details)
        if self.ShouldCreateTargets(algorithm, self.optWeights, lastActiveInsights):
            # symbols with active insights
            lastActiveSymbols = [x.Symbol for x in lastActiveInsights]
            
            # get historical data for all symbols for the last 253 trading days (to get 252 returns)
            history = algorithm.History(lastActiveSymbols, 253, Resolution.Daily)
            
            # empty dictionary for calculations
            calculations = {}
            
            # iterate over all symbols and perform calculations
            for symbol in lastActiveSymbols:
                if (str(symbol) not in history.index or history.loc[str(symbol)].get('close') is None
                or history.loc[str(symbol)].get('close').isna().any()):
                    algorithm.Log('(Portfolio) no historical data for: ' + str(symbol.Value))
                    continue
                else:
                    # add symbol to calculations
                    calculations[symbol] = SymbolData(symbol)
                    try:
                        # get series of log-returns
                        calculations[symbol].CalculateLogReturnSeries(history)
                    except Exception:
                        algorithm.Log('(Portfolio) removing from calculations due to CalculateLogReturnSeries failing: ' + str(symbol.Value))
                        calculations.pop(symbol)
                        continue
            
            # determine target percent for the given insights (check function DetermineTargetPercent for details)
            self.optWeights = self.DetermineTargetPercent(calculations, lastActiveInsights)
            
            if not self.optWeights.isnull().values.any():
                algorithm.Log('(Portfolio) optimal weights: ' + str(self.optWeights))
                
                errorSymbols = {}
                for symbol in lastActiveSymbols:
                    if str(symbol) in self.optWeights:
                        # avoid very small numbers and make them 0
                        if self.optWeights[str(symbol)] <= 1e-10:
                            self.optWeights[str(symbol)] = 0
                        algorithm.Plot('Optimal Allocation', symbol.Value, float(self.optWeights[str(symbol)]))
                        target = PortfolioTarget.Percent(algorithm, symbol, self.optWeights[str(symbol)])
                        if not target is None:
                            targets.append(target)
                        else:
                            errorSymbols[symbol] = symbol

            # update rebalancing time
            if self.rebalancing:
                self.rebalancingTime = self.rebalancingFunc(algorithm.UtcTime)

        # get expired insights and create flatten targets for each symbol
        expiredInsights = self.insightCollection.RemoveExpiredInsights(algorithm.UtcTime)

        expiredTargets = []
        for symbol, f in groupby(expiredInsights, lambda x: x.Symbol):
            if not self.insightCollection.HasActiveInsights(symbol, algorithm.UtcTime) and not symbol in errorSymbols:
                expiredTargets.append(PortfolioTarget(symbol, 0))
                continue

        targets.extend(expiredTargets)
        
        # here we update the next expiry date in the insight collection
        self.nextExpiryTime = self.insightCollection.GetNextExpiryTime()
        if self.nextExpiryTime is None:
            self.nextExpiryTime = UTCMIN

        return targets
        
    def ShouldCreateTargets(self, algorithm, optWeights, lastActiveInsights):
        
        '''
        Description:
            Determine whether we should rebalance the portfolio to keep equal weighting when:
                - It is time to rebalance regardless
                - We want to include some new security in the portfolio
                - We want to modify the direction of some existing security
        Args:
            optWeights: Series containing the current optimal weight for each security
            lastActiveInsights: The last active insights to check
        '''
        
        # it is time to rebalance
        if self.rebalancing and algorithm.UtcTime >= self.rebalancingTime:
            return True
        
        for insight in lastActiveInsights:
            # if there is an insight for a new security that's not invested and it has no existing optimal weight, then rebalance
            if (not algorithm.Portfolio[insight.Symbol].Invested
            and insight.Direction != InsightDirection.Flat
            and str(insight.Symbol) not in optWeights):
                return True
            # if there is an insight to close a long position, then rebalance
            elif algorithm.Portfolio[insight.Symbol].IsLong and insight.Direction != InsightDirection.Up:
                return True
            # if there is an insight to close a short position, then rebalance
            elif algorithm.Portfolio[insight.Symbol].IsShort and insight.Direction != InsightDirection.Down:
                return True
            else:
                continue
            
        return False
        
    def DetermineTargetPercent(self, calculations, lastActiveInsights):
        
        '''
        Description:
            Determine the target percent for each symbol provided
        Args:
            calculations: Dictionary with calculations for symbols
            lastActiveInsights: Dictionary with calculations for symbols
        '''
        
        if self.objectiveFunction == 'equal':
            # give equal weighting to each security
            count = sum(x.Direction != InsightDirection.Flat for x in lastActiveInsights)
            percent = 0 if count == 0 else 1.0 / count
        
            result = {}
            for insight in lastActiveInsights:
                result[str(insight.Symbol)] = insight.Direction * percent
            
            weights = pd.Series(result)
            
            return weights
        
        else:        
            # create a dictionary keyed by the symbols in calculations with a pandas.Series as value to create a dataframe of log-returns
            logReturnsDict = { str(symbol): symbolData.logReturnSeries for symbol, symbolData in calculations.items() }
            logReturnsDf = pd.DataFrame(logReturnsDict)
            
            # portfolio optimizer finds the optimal weights for the given data
            weights = self.optimizer.Optimize(historicalLogReturns = logReturnsDf)
            weights = pd.Series(weights, index = logReturnsDf.columns)
            
            return weights
        
    def OnSecuritiesChanged(self, algorithm, changes):
        
        '''
        Description:
            Event fired each time the we add/remove securities from the data feed
        Args:
            algorithm: The algorithm instance that experienced the change in securities
            changes: The security additions and removals from the algorithm
        '''

        # get removed symbol and invalidate them in the insight collection
        self.removedSymbols = [x.Symbol for x in changes.RemovedSecurities]
        self.insightCollection.Clear(self.removedSymbols)
        
class SymbolData:
    
    ''' Contain data specific to a symbol required by this model '''
    
    def __init__(self, symbol):
        
        self.Symbol = symbol
        self.logReturnSeries = None
    
    def CalculateLogReturnSeries(self, history):
        
        ''' Calculate the log-returns series for each security '''
        
        self.logReturnSeries = np.log(1 + history.loc[str(self.Symbol)]['close'].pct_change(periods = 1).dropna()) # 1-day log-returns
        
### class containing the CustomPortfolioOptimizer -----------------------------------------------------------------------------------------

class CustomPortfolioOptimizer:
    
    '''
    Description:
        Implementation of a custom optimizer that calculates the weights for each asset to optimize a given objective function
    Details:
        Optimization can be:
            - Maximize Portfolio Return
            - Minimize Portfolio Standard Deviation
            - Maximize Portfolio Sharpe Ratio
        Constraints:
            - Weights must be between some given boundaries
            - Weights must sum to 1
    '''
    
    def __init__(self, 
                 minWeight = -1,
                 maxWeight = 1,
                 objFunction = 'std'):
                     
        '''
        Description:
            Initialize the CustomPortfolioOptimizer
        Args:
            minWeight(float): The lower bound on portfolio weights
            maxWeight(float): The upper bound on portfolio weights
            objFunction: The objective function to optimize (return, std, sharpe)
        '''
        
        self.minWeight = minWeight
        self.maxWeight = maxWeight
        self.objFunction = objFunction

    def Optimize(self, historicalLogReturns, covariance = None):
        
        '''
        Description:
            Perform portfolio optimization using a provided matrix of historical returns and covariance (optional)
        Args:
            historicalLogReturns: Matrix of historical log-returns where each column represents a security and each row log-returns for the given date/time (size: K x N)
            covariance: Multi-dimensional array of double with the portfolio covariance of returns (size: K x K)
        Returns:
            Array of double with the portfolio weights (size: K x 1)
        '''
        
        # if no covariance is provided, calculate it using the historicalLogReturns
        if covariance is None:
            covariance = historicalLogReturns.cov()

        size = historicalLogReturns.columns.size # K x 1
        x0 = np.array(size * [1. / size])
        
        # apply equality constraints
        constraints = ({'type': 'eq', 'fun': lambda weights: self.GetBudgetConstraint(weights)})

        opt = minimize(lambda weights: self.ObjectiveFunction(weights, historicalLogReturns, covariance),   # Objective function
                        x0,                                                                                 # Initial guess
                        bounds = self.GetBoundaryConditions(size),                                          # Bounds for variables
                        constraints = constraints,                                                          # Constraints definition
                        method = 'SLSQP')                                                                   # Optimization method: Sequential Least Squares Programming
                        
        return opt['x']

    def ObjectiveFunction(self, weights, historicalLogReturns, covariance):
        
        '''
        Description:
            Compute the objective function
        Args:
            weights: Portfolio weights
            historicalLogReturns: Matrix of historical log-returns
            covariance: Covariance matrix of historical log-returns
        '''
        
        # calculate the annual return of portfolio
        annualizedPortfolioReturns = np.sum(historicalLogReturns.mean() * 252 * weights)

        # calculate the annual standard deviation of portfolio
        annualizedPortfolioStd = np.sqrt( np.dot(weights.T, np.dot(covariance * 252, weights)) )
        
        if annualizedPortfolioStd == 0:
            raise ValueError(f'CustomPortfolioOptimizer.ObjectiveFunction: annualizedPortfolioStd cannot be zero. Weights: {weights}')
        
        # calculate annual sharpe ratio of portfolio
        annualizedPortfolioSharpeRatio = (annualizedPortfolioReturns / annualizedPortfolioStd)
            
        if self.objFunction == 'sharpe':
            return -annualizedPortfolioSharpeRatio # convert to negative to be minimized
        elif self.objFunction == 'return':
            return -annualizedPortfolioReturns # convert to negative to be minimized
        elif self.objFunction == 'std':
            return annualizedPortfolioStd
        else:
            raise ValueError(f'CustomPortfolioOptimizer.ObjectiveFunction: objFunction input has to be one of sharpe, return or std')

    def GetBoundaryConditions(self, size):
        
        ''' Create the boundary condition for the portfolio weights '''
        
        return tuple((self.minWeight, self.maxWeight) for x in range(size))

    def GetBudgetConstraint(self, weights):
        
        ''' Define a budget constraint: the sum of the weights equal to 1 '''
        
        return np.sum(weights) - 1