#This program was taken from QuantConnect's sample Execution modules 
import numpy as np


class StandardDeviationExecutionModel(ExecutionModel):
    '''Execution model that submits orders while the current market prices is at least the configured number of standard
     deviations away from the mean in the favorable direction (below/above for buy/sell respectively)'''

    def __init__(self,
                 period = 60,
                 deviations = 2,
                 resolution = Resolution.Minute):
        '''Initializes a new instance of the StandardDeviationExecutionModel class
        Args:
            period: Period of the standard deviation indicator
            deviations: The number of deviations away from the mean before submitting an order
            resolution: The resolution of the STD and SMA indicators'''
        self.period = period
        self.deviations = deviations
        self.resolution = resolution
        self.targetsCollection = PortfolioTargetCollection()
        self.symbolData = {}

        # Gets or sets the maximum order value in units of the account currency.
        # This defaults to $20,000. For example, if purchasing a stock with a price
        # of $100, then the maximum order size would be 200 shares.
        self.MaximumOrderValue = 20000


    def Execute(self, algorithm, targets):
        '''Executes market orders if the standard deviation of price is more
       than the configured number of deviations in the favorable direction.
       Args:
           algorithm: The algorithm instance
           targets: The portfolio targets'''
        self.targetsCollection.AddRange(targets)

        # for performance we check count value, OrderByMarginImpact and ClearFulfilled are expensive to call
        if self.targetsCollection.Count > 0:
            for target in self.targetsCollection.OrderByMarginImpact(algorithm):
                symbol = target.Symbol

                # calculate remaining quantity to be ordered
                unorderedQuantity = OrderSizing.GetUnorderedQuantity(algorithm, target)

                # fetch our symbol data containing our STD/SMA indicators
                data = self.symbolData.get(symbol, None)
                if data is None: return

                # check order entry conditions
                if data.STD.IsReady and self.PriceIsFavorable(data, unorderedQuantity):
                    # Adjust order size to respect the maximum total order value
                    orderSize = OrderSizing.GetOrderSizeForMaximumValue(data.Security, self.MaximumOrderValue, unorderedQuantity)

                    if orderSize != 0:
                        algorithm.MarketOrder(symbol, orderSize)

            self.targetsCollection.ClearFulfilled(algorithm)


    def OnSecuritiesChanged(self, algorithm, changes):
        '''Event fired each time the we add/remove securities from the data feed
        Args:
            algorithm: The algorithm instance that experienced the change in securities
            changes: The security additions and removals from the algorithm'''
        for added in changes.AddedSecurities:
            if added.Symbol not in self.symbolData:
                self.symbolData[added.Symbol] = SymbolData(algorithm, added, self.period, self.resolution)

        for removed in changes.RemovedSecurities:
            # clean up data from removed securities
            symbol = removed.Symbol
            if symbol in self.symbolData:
                if self.IsSafeToRemove(algorithm, symbol):
                    data = self.symbolData.pop(symbol)
                    algorithm.SubscriptionManager.RemoveConsolidator(symbol, data.Consolidator)


    def PriceIsFavorable(self, data, unorderedQuantity):
        '''Determines if the current price is more than the configured
       number of standard deviations away from the mean in the favorable direction.'''
        sma = data.SMA.Current.Value
        deviations = self.deviations * data.STD.Current.Value
        if unorderedQuantity > 0:
            return data.Security.BidPrice < sma - deviations
        else:
            return data.Security.AskPrice > sma + deviations


    def IsSafeToRemove(self, algorithm, symbol):
        '''Determines if it's safe to remove the associated symbol data'''
        # confirm the security isn't currently a member of any universe
        return not any([kvp.Value.ContainsMember(symbol) for kvp in algorithm.UniverseManager])

class SymbolData:
    def __init__(self, algorithm, security, period, resolution):
        symbol = security.Symbol
        self.Security = security
        self.Consolidator = algorithm.ResolveConsolidator(symbol, resolution)

        smaName = algorithm.CreateIndicatorName(symbol, f"SMA{period}", resolution)
        self.SMA = SimpleMovingAverage(smaName, period)
        algorithm.RegisterIndicator(symbol, self.SMA, self.Consolidator)

        stdName = algorithm.CreateIndicatorName(symbol, f"STD{period}", resolution)
        self.STD = StandardDeviation(stdName, period)
        algorithm.RegisterIndicator(symbol, self.STD, self.Consolidator)

        # warmup our indicators by pushing history through the indicators
        history = algorithm.History(symbol, period, resolution)
        if 'close' in history:
            history = history.close.unstack(0).squeeze()
            for time, value in history.iteritems():
                self.SMA.Update(time, value)
                self.STD.Update(time, value)