#This program was taken from QuantConnect's sample portfolio construction modules 
from itertools import groupby
from datetime import datetime, timedelta

class EqualWeightingPortfolioConstructionModel(PortfolioConstructionModel):
    '''Provides an implementation of IPortfolioConstructionModel that gives equal weighting to all securities.
    The target percent holdings of each security is 1/N where N is the number of securities.
    For insights of direction InsightDirection.Up, long targets are returned and
    for insights of direction InsightDirection.Down, short targets are returned.'''

    def __init__(self, rebalance = Resolution.Daily, portfolioBias = PortfolioBias.LongShort):
        '''Initialize a new instance of EqualWeightingPortfolioConstructionModel
        Args:
            rebalance: Rebalancing parameter. If it is a timedelta, date rules or Resolution, it will be converted into a function.
                              If None will be ignored.
                              The function returns the next expected rebalance time for a given algorithm UTC DateTime.
                              The function returns null if unknown, in which case the function will be called again in the
                              next loop. Returning current time will trigger rebalance.
            portfolioBias: Specifies the bias of the portfolio (Short, Long/Short, Long)'''
        self.portfolioBias = portfolioBias

        # If the argument is an instance of Resolution or Timedelta
        # Redefine rebalancingFunc
        rebalancingFunc = rebalance
        if isinstance(rebalance, int):
            rebalance = Extensions.ToTimeSpan(rebalance)
        if isinstance(rebalance, timedelta):
            rebalancingFunc = lambda dt: dt + rebalance
        if rebalancingFunc:
            self.SetRebalancingFunc(rebalancingFunc)

    def DetermineTargetPercent(self, activeInsights):
        '''Will determine the target percent for each insight
        Args:
            activeInsights: The active insights to generate a target for'''
        result = {}

        # give equal weighting to each security
        count = sum(x.Direction != InsightDirection.Flat and self.RespectPortfolioBias(x) for x in activeInsights)
        percent = 0 if count == 0 else 1.0 / count
        for insight in activeInsights:
            result[insight] = (insight.Direction if self.RespectPortfolioBias(insight) else InsightDirection.Flat) * percent
        return result

    def RespectPortfolioBias(self, insight):
        '''Method that will determine if a given insight respects the portfolio bias
        Args:
            insight: The insight to create a target for
        '''
        return self.portfolioBias == PortfolioBias.LongShort or insight.Direction == self.portfolioBias