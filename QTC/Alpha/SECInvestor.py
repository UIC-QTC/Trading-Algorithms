#This program was taken from QuantConnect's sample Alpha modules 
from QuantConnect.Data.Custom.SEC import *
from QuantConnect.Data.Custom.CBOE import *
from QuantConnect.Data.Custom.Fred import *
from QuantConnect.Data.Custom.USEnergy import *

class SEC(AlphaModel):

    def __init__(self,
                 period = 120,
                 resolution = Resolution.Daily):
        
        self.period = period
        self.resolution = resolution
        self.insightPeriod = Time.Multiply(Extensions.ToTimeSpan(resolution), period)
        
        # this dictionary stores all current trading stocks
        self.symbolDataBySymbol ={} 
        resolutionString = Extensions.GetEnumString(resolution, Resolution)
        
        self.Name = '{}({},{})'.format(self.__class__.__name__, period, resolutionString)
        self.month=None

    def Update(self, algorithm, data):
        
        insights = []
        
        #Checks if insights were already generated this month if so return null
        if algorithm.Time.month == self.month:
            return []
        self.month = algorithm.Time.month
        
        for symbol, SymbolData in self.symbolDataBySymbol.items():
            '''If # of characters in SEC report is > x then buy'''
            for report in data.Get(SECReport10Q).Values:
                reportTextLength = sum([len(i.Text) for i in report.Report.Documents])
                
                if int(report.Report.PublicDocumentCount) > 1000:
                    insights.append(Insight.Price(symbol, self.insightPeriod, InsightDirection.Up))
                elif int(report.Report.PublicDocumentCount) > 500:
                    insights.append(Insight.Price(symbol, self.insightPeriod, InsightDirection.Down))
                else:
                    insights.append(Insight.Price(symbol, self.insightPeriod, InsightDirection.Flat))
        
        return insights
  
    def OnSecuritiesChanged(self, algorithm, changes):
        '''
        Event fired each time the we add/remove securities from the data feed
        Args:
            algorithm: The algorithm instance that experienced the change in securities
            changes: The security additions and removals from the algorithm'''

        addedSymbols = [ x.Symbol for x in changes.AddedSecurities if x not in self.symbolDataBySymbol]
                    
        for y in  changes.RemovedSecurities:
            for subscription in algorithm.SubscriptionManager.Subscriptions:
                if subscription in changes.RemovedSecurities:
                    self.symbolDataBySymbol.pop(subscription.Symbol, None)
                    subscription.Consolidators.Clear()
            if algorithm.Portfolio[y.Symbol].Invested:
                algorithm.Liquidate(y.Symbol)
                
            self.symbolDataBySymbol.pop(y.Symbol)
            algorithm.RemoveSecurity(y.Symbol)
        #Removes any old securities from our array liquidates our holdings and removes from alg
   
        for symbol in addedSymbols:
            #pulls SEC filings for each new asset in our universe
            earningsFiling = algorithm.AddData(SECReport10Q, symbol, Resolution.Daily).Symbol
            # Request 120 days of history with the SECReport10Q IBM custom data Symbol
            history = algorithm.History(SECReport10Q, earningsFiling, 120, Resolution.Daily)
         
            #appends new data to array
            self.symbolDataBySymbol[symbol] = SymbolData(symbol)
            
class SymbolData:
    '''Contains data specific to a symbol required by this model'''
    def __init__(self, symbol):
        self.Symbol = symbol