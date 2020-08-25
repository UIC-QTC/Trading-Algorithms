#This program was extended from an example alpha model on QuantConnect
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from scipy.stats import t #We use T-distribution to show the liklieness 

class howdydoo(AlphaModel):
#This alpha model measure the probability that one asset is going to outperform another asset based on our self.max_prob
    def __init__(self, period =45 ,resolution = Resolution.Daily):
                   
        self.back_period = period
        self.resolution = resolution
        self.insightPeriod = Time.Multiply(Extensions.ToTimeSpan(resolution), period)
        resolutionString = Extensions.GetEnumString(resolution, Resolution)
        self.Name = '{}({},{})'.format(self.__class__.__name__, period, resolutionString)
        self.Securities=[]#array for all of our assets
        self.month=None
        self.max_prob = 0.75   #Probability that must be achieved before we think stock B is going to outperform stock A
        self.points=[] #array of stocks that meet the criterion
    
    def Update(self, algorithm, data):
        insights=[]
        
         #Checks if insights were already generated this month if so return null
        if algorithm.Time.month == self.month:
            return []
        self.month = algorithm.Time.month
        
        for x in self.points:
            insights.append(Insight.Price(x, self.insightPeriod, InsightDirection.Up))
        #If our stock gets added we think the likliness of it increasing is significant, emitt an insight signal
        return insights
        
    def OnSecuritiesChanged(self, algorithm, changes):
        #Clear out self.points array to remove old picks
        self.points.clear()
        
        #Update our self.Securities array
        for security in changes.AddedSecurities:
            self.Securities.append(security)

        for security in changes.RemovedSecurities:
            if security in self.Securities:
                self.Securities.remove(security)
                
        symbols = [ x.Symbol for x in self.Securities ]
        #need to call all securities in our universe to calculate correlation
        if len(symbols)==0: return
        
        #Pulls history
        history = algorithm.History(symbols, self.back_period, self.resolution)["close"].unstack(level=0) 
       
        if not history.empty:
            
        # if we are trading
            daily_rtrn = history.pct_change().dropna() # or np.log(self.price  self.price.shift(1)).dropna()
            n = len(daily_rtrn.index); sqrt_n = np.sqrt(n)
            
            for i,tick1 in enumerate(symbols): 
               
                for j,tick2 in enumerate(symbols):
                   
                    if i < j: # upper part matrix(tkr_1, tkr_2); (n^2 - n)  2 operations
                        rtrn_diff = daily_rtrn[tick1] - daily_rtrn[tick2]
                        if np.std(rtrn_diff)!=0:
                            x = np.mean(rtrn_diff) / np.std(rtrn_diff) * np.sqrt(n) # t_stat = avg(diff)(std(diff)sqrt(n))

                            if x  >0 :  # x0 - tkr_1 better than tkr_2
                                prob = (1 - t.sf(x, n-1))  # T-dist cumulative probability Prob(Xx)
                                if prob > self.max_prob and tick1 not in self.points :
                                    self.points.append(tick1)
                            else: 
                                prob = (1 - t.sf(-x, n-1))               
                                if prob > self.max_prob and tick2 not in self.points :
                                    self.points.append(tick2)