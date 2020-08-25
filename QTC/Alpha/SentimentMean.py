# This program is entirely original work of Q.T.C. 
from QuantConnect.Data.Custom.Tiingo import *
from datetime import datetime, timedelta
import numpy as np

class SentimentWindow(AlphaModel):
    
    def __init__(self): 
        self.newsData = {}

        self.wordScores = {
            "bad": -0.5, "good": 0.5, "negative": -0.5, 
            "great": 0.5, "growth": 0.5, "fail": -0.5, 
            "failed": -0.5, "success": 0.5, "nailed": 0.5,
            "beat": 0.5, "missed": -0.5, "profitable": 0.5,
            "beneficial": 0.5, "right": 0.5, "positive": 0.5, 
            "large":0.5, "attractive": 0.5, "sound": 0.5, 
            "excellent": 0.5, "wrong": -0.5, "unproductive": -0.5, 
            "lose": -0.5, "missing": -0.5, "mishandled": -0.5, 
            "un_lucrative": -0.5, "up": 0.5, "down": -0.5,
            "unproductive": -0.5, "poor": -0.5, "wrong": -0.5,
            "worthwhile": 0.5, "lucrative": 0.5, "solid": 0.5,
            "beat": 0.5, "missed": -0.5
        }
        
        self.lastday = -1
        
    def Update(self, algorithm, data):

        insights = []
        
        day = algorithm.Time.hour
        if day == self.lastday:
            return insights
        self.lastday = day
        
        news = data.Get(TiingoNews) 

        for article in news.Values:
            words = article.Description.lower().split(" ")
            score = sum([self.wordScores[word] for word in words
                if word in self.wordScores])
                
            if score == 0.0:
                continue
            
            symbol = article.Symbol.Underlying 
    
            self.newsData[symbol].Window.Add(score)
            
            if self.newsData[symbol].Window.Count < 2:
                return insights
                
            currentWindow = self.newsData[symbol].Window[0]
                
            sentimentMean = sum(self.newsData[symbol].Window)/self.newsData[symbol].Window.Count
            
            if currentWindow > (sentimentMean*1.1) and currentWindow > 0:
                insights.append(Insight.Price(symbol, timedelta(days=1), InsightDirection.Up, None, None))
            elif currentWindow <= 0:
                insights.append(Insight.Price(symbol, timedelta(days=1), InsightDirection.Flat, None, None))
            
        return insights
    
    def OnSecuritiesChanged(self, algorithm, changes):

        for security in changes.AddedSecurities:
            symbol = security.Symbol
            newsAsset = algorithm.AddData(TiingoNews, symbol)
            self.newsData[symbol] = NewsData(newsAsset.Symbol)

        for security in changes.RemovedSecurities:
            newsData = self.newsData.pop(security.Symbol, None)
            if newsData is not None:
                algorithm.RemoveSecurity(newsData.Symbol)
                
class NewsData():
    def __init__(self, symbol):
        self.Symbol = symbol
        #two month rolling window if insights are emitted daily
        self.Window = RollingWindow[float](120)