# This program is entirely original work of Q.T.C. 

from QuantConnect.Algorithm.Framework.Alphas import *
class example(AlphaModel):   
    def __init__(self,period = 45,resolution = Resolution.Daily):
        
        self.period = period
        self.resolution = resolution
        self.insightPeriod = Time.Multiply(Extensions.ToTimeSpan(self.resolution), self.period)
        self.symbolDataBySymbol ={} # this is just an dictcionary
        
        self.day=None
       
        
        resolutionString = Extensions.GetEnumString(resolution, Resolution)
        self.Name = '{}({},{})'.format(self.__class__.__name__, period, resolutionString)
  
    def Update(self, algorithm, data):
          
        insights = []
        #Checks if insights were already generated today (because of indicator resolution) if so return empty array
        if algorithm.Time.day == self.day:
            return []
        self.day = algorithm.Time.day
        
        
        
       
        for symbol, symbolData in self.symbolDataBySymbol.items():
            if symbol.Value=="SPY" or  symbol.Value=="BND":
                continue
            
            value = algorithm.Securities[symbol].Price
            
            std=symbolData.STD
            ema=symbolData.EMA
            
           # if not std.IsReady:
                #Here we have the dilemna we can either output flat insights to ensure we have consistent insights per day (which we do) or 
                #just continue and not get an backtesting error for a specific security not having pricing data
                
                #insights.append(Insight.Price(symbol, timedelta(days=1), InsightDirection.Flat,0.0025, 1.00,"ReversiontotheMean", .5))
              #  continue
           # if not ema.IsReady:
                #insights.append(Insight.Price(symbol, timedelta(days=1), InsightDirection.Flat,0.0025, 1.00,"ReversiontotheMean", .5))   
                #continue
          
            if value< (ema.Current.Value-std.Current.Value):
                insights.append(Insight.Price(symbol, timedelta(days=1), InsightDirection.Up, 0.0025, 1.00,"ReversiontotheMean", .5))
            elif value> (ema.Current.Value+std.Current.Value):
                insights.append(Insight.Price(symbol, timedelta(days=1), InsightDirection.Down,0.0025, 1.00,"ReversiontotheMean", .5))
            else:
                insights.append(Insight.Price(symbol, timedelta(days=1), InsightDirection.Flat,0.0025, 1.00,"ReversiontotheMean", .5))
        
        return insights


    def OnSecuritiesChanged(self, algorithm, changes):
 
        
    
        addedSymbols = [ x.Symbol for x in changes.AddedSecurities if x not in self.symbolDataBySymbol]
                    
        for y in  changes.RemovedSecurities:
            for subscription in algorithm.SubscriptionManager.Subscriptions:
                if subscription in changes.RemovedSecurities:
                    self.symbolDataBySymbol.pop(subscription.Symbol, None)
                    subscription.Consolidators.Clear()
          
                
            self.symbolDataBySymbol.pop(y.Symbol)
        
        #Removes any old securities from our array 
   
   
        history = algorithm.History(addedSymbols, self.period, self.resolution)
        #pulls history for all new symbols
     
        for symbol in addedSymbols:
            
            std=algorithm.STD(symbol, self.period, self.resolution)
            ema=algorithm.EMA(symbol, self.period-15, self.resolution)
            #for each new symbol, generate an instance of the indicator rsi
      
            if not history.empty:
                ticker = SymbolCache.GetTicker(symbol)
                #if history isnt empty set the ticker as the symbol
                
                if ticker not in history.index.levels[0]:
                   
                    continue
                # if for some reason history isnt there, output a log
                
                for tuple in history.loc[ticker].itertuples():
             
                    std.Update(tuple.Index, tuple.close)
                    ema.Update(tuple.Index, tuple.close)
            self.symbolDataBySymbol[symbol] = SymbolData(symbol, std,ema)
 
        
       
class SymbolData:
    '''Contains data specific to a symbol required by this model'''
    def __init__(self, symbol, std,ema):
        self.Symbol = symbol
      
        self.STD=std
        self.EMA=ema