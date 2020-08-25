#This program was extended from an example alpha model on QuantConnect
class MACDTrendAlgorithm(AlphaModel):

    def __init__(self,period = 75, movingaverage=MovingAverageType.Exponential,resolution = Resolution.Daily):
        
        self.macdFastperiod = 12
        self.macdSlowperiod = 26
        self.macdSignalperiod = 9
        
        self.tolerance = 0.005
        
        self.period = period
        self.resolution = resolution
        self.ma = movingaverage
        self.symbolDataBySymbol = {}
        self.day=None
        
        self.insightPeriod = Time.Multiply(Extensions.ToTimeSpan(self.resolution), self.period)
        resolutionString = Extensions.GetEnumString(resolution, Resolution)
        self.Name = '{}({},{})'.format(self.__class__.__name__, period, resolutionString)
        
    def Update(self, algorithm, data):
        
        insights = []
        
        #Checks if insights were already generated (daily) if so return an empty array. 
        if algorithm.Time.day == self.day:
            return []
        self.day = algorithm.Time.day
        
        for symbol, SymbolData in self.symbolDataBySymbol.items():
            macdINSIGHT = SymbolData.MACD
            if not macdINSIGHT.IsReady:
                return []
            
            signalDeltaPercent = (macdINSIGHT.Current.Value - macdINSIGHT.Signal.Current.Value)/macdINSIGHT.Fast.Current.Value
   
            # if our macd is greater than signal, buy
            if signalDeltaPercent > self.tolerance:  # 0.01%
            
            # longterm says buy as well
                insights.append(Insight.Price(symbol, self.insightPeriod, InsightDirection.Up))
                    
            # if our macd is less than signal, sell
            elif signalDeltaPercent < -self.tolerance:
                insights.append(Insight.Price(symbol, self.insightPeriod, InsightDirection.Down))
            
            # if our macd is within our bounds, do nothing        
            else: 
                insights.append(Insight.Price(symbol, self.insightPeriod, InsightDirection.Flat))
                 
        return insights
       
    def OnSecuritiesChanged(self, algorithm, changes):
        addedSymbols = [ x.Symbol for x in changes.AddedSecurities if x not in self.symbolDataBySymbol]
                    
        for y in  changes.RemovedSecurities:
            for subscription in algorithm.SubscriptionManager.Subscriptions:
                if subscription in changes.RemovedSecurities:
                    self.symbolDataBySymbol.pop(subscription.Symbol, None)
                    subscription.Consolidators.Clear()
            if algorithm.Portfolio[y.Symbol].Invested:# not in self.removed :
                algorithm.Liquidate(y.Symbol)
                
            self.symbolDataBySymbol.pop(y.Symbol)
            algorithm.RemoveSecurity(y.Symbol)
        #Removes any old securities from our array liquidates our holdings and removes from alg
   
        history = algorithm.History(addedSymbols, self.period, self.resolution)
        #pulls history for all new symbols
 
        for symbol in addedSymbols:
            
            macd = algorithm.MACD(symbol, self.macdFastperiod, self.macdSlowperiod, self.macdSignalperiod, self.ma, self.resolution)
            if not history.empty:
                ticker = SymbolCache.GetTicker(symbol)
                
                if ticker not in history.index.levels[0]:
                    continue
                
                for tuple in history.loc[ticker].itertuples():
                    macd.Update(tuple.Index, tuple.close)
                    
            self.symbolDataBySymbol[symbol] = SymbolData(symbol, macd)

class SymbolData:
    '''Contains data specific to a symbol required by this model'''
    def __init__(self, symbol, macd):
        self.Symbol = symbol
        self.MACD   = macd