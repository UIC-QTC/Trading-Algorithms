#This program is in the classic algorithm style and is original work of Q.T.C. 
from QuantConnect.Data.Custom.Tiingo import *
from datetime import datetime, timedelta
import numpy as np

class GunStocks(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2015, 1, 1)
        self.SetCash(1000000)
        
        self.tickers = ["AXON", "AOBC", "RGR", "VSTO", "SPWH", "OLN", "SWBI"]
        
        symbols = []
        
        for i in self.tickers:
            symbols.append(Symbol.Create(i, SecurityType.Equity, Market.USA))
        
        self.UniverseSettings.Resolution = Resolution.Daily
        self.SetUniverseSelection(ManualUniverseSelectionModel(symbols))
        self.SetAlpha(GunStocksAlphaModel())
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel()) 
        self.SetExecution(ImmediateExecutionModel()) 
        self.SetRiskManagement(TrailingStopRiskManagementModel(0.02))

class GunStocksAlphaModel(AlphaModel):
    
    def __init__(self, news_history_length = 100): 
        self.news_history_length = news_history_length
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
            "conflict": 0.5, "peace": -0.5, "contracts": 0.5, "equipment": 0.5,
            "war": 0.5, "scandal": -0.5, "bribe": -0.5, "tax": -0.5,
            "gun": 0.5, "stocks": 0.5, "stock": 0.5, "invest": 0.5,
            "optamistic": 0.5, "sell": -0.5, "buy": 0.5, "gained": 0.5,
            "lost": -0.5, "riots": 0.5, "riot": 0.5, "terrorism": 0.5,
            "frightened": 0.5, "violence": 0.5
            
        }
        
        self.senators = {
            1999 : "R",
            2000 : "R",
            2001 : "D",
            2002 : "D", 
            2003 : "R",
            2004 : "R", 
            2005 : "R",
            2006 : "R",
            2007 : "D",
            2008 : "D",
            2009 : "D",
            2010 : "D",
            2011 : "D",
            2012 : "D",
            2013 : "D",
            2014 : "D",
            2015 : "R",
            2016 : "R",
            2017 : "R",
            2018 : "R",
            2019 : "R",
            2020 : "R"
        }
    
        self.lastmonth = -1
        
    def Update(self, algorithm, data):

        # Gather news
        news = data.Get(TiingoNews) 
        for article in news.Values:
            words = article.Description.lower().split(" ")
            score = sum([self.wordScores[word] for word in words
                if word in self.wordScores])
            
            symbol = article.Symbol.Underlying 
            
            self.newsData[symbol].Window.Add(score)

        insights = []
        
        month = algorithm.Time.month
        if month == self.lastmonth or \
            not (algorithm.Time.hour == 0 and algorithm.Time.minute == 0 and algorithm.Time.second == 0):
            return insights
        self.lastmonth = month

        politicalPoints = 3 * (1 if self.senators[algorithm.Time.year] == 'D' else -1)
        
        for symbol in self.newsData.keys():
            sentiment = sum(self.newsData[symbol].Window) + politicalPoints 
            if sentiment > 10:
                insights.append(Insight.Price(symbol, timedelta(days=5), InsightDirection.Up, None, None))
            elif sentiment < -1:
                insights.append(Insight.Price(symbol, timedelta(days=5), InsightDirection.Down, None, None))
        return insights
    
    def OnSecuritiesChanged(self, algorithm, changes):

        for security in changes.AddedSecurities:
            symbol = security.Symbol
            news_symbol = algorithm.AddData(TiingoNews, symbol).Symbol
            self.newsData[symbol] = NewsData(news_symbol, self.news_history_length)

        for security in changes.RemovedSecurities:
            newsData = self.newsData.pop(security.Symbol, None)
            if newsData is not None:
                algorithm.RemoveSecurity(newsData.Symbol) 
                
class NewsData():
    def __init__(self, symbol, news_history_length):
        self.Symbol = symbol
        self.Window = RollingWindow[float](news_history_length)