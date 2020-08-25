#This program was extended from an example alpha model on QuantConnect
class FundamentalData(AlphaModel):

    def __init__(self):
        self.lastDay = -1
        self.Securities=[]
    def Update(self, algorithm, data):
        
        insights = []
        
        if self.lastDay == algorithm.Time.day:
            return insights 
            
        self.lastDay = algorithm.Time.day
        
        for security in self.Securities:#algorithm.ActiveSecurities.Values:
            direction = 1 if security.Fundamentals.ValuationRatios.EarningYield > 0 else -1 
            insights.append(Insight.Price(security.Symbol, timedelta(28), direction)) 
        return insights

    def OnSecuritiesChanged(self, algorithm, changes):

         #Update our self.Securities array
        for security in changes.AddedSecurities:
            self.Securities.append(security)

        for security in changes.RemovedSecurities:
            if security in self.Securities:
                self.Securities.remove(security)