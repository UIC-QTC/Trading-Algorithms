#This program was taken from QuantConnect's sample Risk Management modules 

class MaximumDrawdownPercentPortfolio(RiskManagementModel):
    '''Provides an implementation of IRiskManagementModel that limits the drawdown of the portfolio to the specified percentage.'''

    def __init__(self, maximumDrawdownPercent = 0.05, isTrailing = False):
        '''Initializes a new instance of the MaximumDrawdownPercentPortfolio class
        Args:
            maximumDrawdownPercent: The maximum percentage drawdown allowed for algorithm portfolio compared with starting value, defaults to 5% drawdown</param>
            isTrailing: If "false", the drawdown will be relative to the starting value of the portfolio.
                        If "true", the drawdown will be relative the last maximum portfolio value'''
        self.maximumDrawdownPercent = -abs(maximumDrawdownPercent)
        self.isTrailing = isTrailing
        self.initialised = False
        self.portfolioHigh = 0;

    def ManageRisk(self, algorithm, targets):
        '''Manages the algorithm's risk at each time step
        Args:
            algorithm: The algorithm instance
            targets: The current portfolio targets to be assessed for risk'''
        currentValue = algorithm.Portfolio.TotalPortfolioValue

        if not self.initialised:
            self.portfolioHigh = currentValue   # Set initial portfolio value
            self.initialised = True

        # Update trailing high value if in trailing mode
        if self.isTrailing and self.portfolioHigh < currentValue:
            self.portfolioHigh = currentValue
            return []   # return if new high reached

        pnl = self.GetTotalDrawdownPercent(currentValue)
        if pnl < self.maximumDrawdownPercent:
            return [ PortfolioTarget(target.Symbol, 0) for target in targets ]

        return []

    def GetTotalDrawdownPercent(self, currentValue):
        return (float(currentValue) / float(self.portfolioHigh)) - 1.0