from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Algorithm.Framework")

from System import *
from QuantConnect import *
from QuantConnect.Algorithm import *
from QuantConnect.Algorithm.Framework import *
from QuantConnect.Algorithm.Framework.Alphas import AlphaModel, Insight, InsightType, InsightDirection

class BuyAndHoldAlphaCreationModel(AlphaModel):
    
    '''
    Description:
        This Alpha model creates InsightDirection.Up (to go Long) for a duration of 1 day, every day for all active securities in our Universe
    Details:
        The important thing to understand here is the concept of Insight:
            - A prediction about the future of the security, indicating an expected Up, Down or Flat move
            - This prediction has an expiration time/date, meaning we think the insight holds for some amount of time
            - In the case of a Buy and Hold strategy, we are just updating every day the Up prediction for another extra day
            - In other words, every day we are making the conscious decision of staying invested in the security one more day
    '''

    def __init__(self, resolution = Resolution.Daily):
        
        self.insightExpiry = Time.Multiply(Extensions.ToTimeSpan(resolution), 0.25) # insight duration
        self.insightDirection = InsightDirection.Up # insight direction
        self.securities = [] # list to store securities to consider
        
    def Update(self, algorithm, data):

        insights = [] # list to store the new insights to be created
        
        # loop through securities and generate insights
        for security in self.securities:
            # check if there's new data for the security or we're already invested
            # if there's no new data but we're invested, we keep updating the insight since we don't really need to place orders
            if data.ContainsKey(security.Symbol) or algorithm.Portfolio[security.Symbol].Invested:
                # append the insights list with the prediction for each symbol
                insights.append(Insight.Price(security.Symbol, self.insightExpiry, self.insightDirection))
            else:
                algorithm.Log('(Alpha) excluding this security due to missing data: ' + str(security.Symbol.Value))
            
        return insights
        
    def OnSecuritiesChanged(self, algorithm, changes):
        
        '''
        Description:
            Event fired each time the we add/remove securities from the data feed
        Args:
            algorithm: The algorithm instance that experienced the change in securities
            changes: The security additions and removals from the algorithm
        '''
        
        # add new securities
        for added in changes.AddedSecurities:
            self.securities.append(added)

        # remove securities
        for removed in changes.RemovedSecurities:
            if removed in self.securities:
                self.securities.remove(removed)