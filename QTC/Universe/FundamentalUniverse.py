# This program is entirely original work of Q.T.C. 
from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel 
from QuantConnect.Data.Custom.SEC import *
from Selection.OptionUniverseSelectionModel import OptionUniverseSelectionModel

from datetime import timedelta, datetime
from math import ceil
from itertools import chain
import numpy as np

class universe(FundamentalUniverseSelectionModel):

    def __init__(self, filterFineData = True, universeSettings = None, securityInitializer = None):
        super().__init__(filterFineData, universeSettings, securityInitializer)

        # Number of stocks in Coarse Universe
        self.NumberOfSymbolsCoarse = 2500
        # Number of sorted stocks in the fine selection subset using the valuation ratio, EV to EBITDA (EV/EBITDA)
        self.NumberOfSymbolsFine =  250
        # Final number of stocks in security list, after sorted by the valuation ratio, Return on Assets (ROA)
        self.NumberOfSymbolsInPortfolio = 10
       
        self.lastmonth = -1
        self.dollarVolumeBySymbol = {}

    def SelectCoarse(self, algorithm, coarse):

        month= algorithm.Time.month
        if month == self.lastmonth:
            return Universe.Unchanged
        self.lastmonth= month

        # sort the stocks by dollar volume and take the top 2000
        top = sorted([x for x in coarse if x.HasFundamentalData],
                    key=lambda x: x.DollarVolume, reverse=True)[:self.NumberOfSymbolsCoarse]
        
        #assigns all the stocks from price to dollarVolumeBySymbol
        self.dollarVolumeBySymbol = { i.Symbol: i.DollarVolume for i in top }

        return list(self.dollarVolumeBySymbol.keys())

    def SelectFine(self, algorithm, fine):
       
        self.priceAllowance = 180
        
        '''
        
        @ is used to show which metrics are currently implemented
        
        Metrics:
        -Institutional Holdings (Data does not exist on QC, but can use custom data)
        -Financial Strength
            Current Ratio  @
            Quick Ratio    @
            Debt to Equity Ratio  @
            Long Term Debt to Equity Ratio   @
            Interest Coverage Ratio @
            
        -Suitable Growth (Sustainable Growth Rate)  @
            
        -Industry Comparison (Willim plement last)
        
        -Management and Equity
            Return on Assets 5YR average     
            ROA  @
            Return on Equity    
            Gross profit margin
            Inventory turnover
            Selling, general, and administrative expenses to net sales
            ROI
            Operating Margin 
            Return on Sales
            Free cash flow from operations
            FCF     @
            Net Income per Employee
        
        -Analyst Opinion (Need to build a web scraper that pulls analyst opinion data from WSJ Markets)
        
        -Leverage and Liquidity
            Calculate Leverage
                Debt to assets
                Debt to capital
                Long term debt to capital   @
                Asset to equity
                (Debt to EBITDA)
            Liquidity
                Cash ratio
                Free Cash Flow
        
        -Fundamental Variables
            (Need to conduct research on this)
            Price to Earnings Ratio
            Returns on Equity Ratio
            Price to Book Ratio
            Profit Margins
            PEG    @
        
        '''
        filteredFine = [x for x in fine if x.CompanyReference.CountryId == "USA"
                                        and x.Price > self.priceAllowance
                                        and (x.CompanyReference.PrimaryExchangeID == "NYS" or x.CompanyReference.PrimaryExchangeID == "NAS")
                                        and (algorithm.Time - x.SecurityReference.IPODate).days > 700
                                        and (x.EarningReports.BasicAverageShares.ThreeMonths * x.EarningReports.BasicEPS.TwelveMonths * x.ValuationRatios.PERatio >= 5e10)
                                    ]
                                    
        self.ratingsDict = {}
        
        for ticker in filteredFine:
            rating = 0
            
            '''Financial Strength'''
            if (ticker.OperationRatios.QuickRatio.ThreeMonths) >= 1.0:
                rating += 1
            if 2.0 >= (ticker.OperationRatios.CurrentRatio.ThreeMonths) >= 1.2:
                rating += 1
            if (ticker.OperationRatios.TotalDebtEquityRatioGrowth.OneYear) <= 1.0:
                rating += 1
            if (ticker.OperationRatios.LongTermDebtEquityRatio.OneYear) < 1.0:
                rating += 1
            if (ticker.OperationRatios.InterestCoverage.ThreeMonths) >= 3.0:
                rating += 1
                
            '''Suitable Growth'''
            if (ticker.ValuationRatios.SustainableGrowthRate) >= 0.07:
                rating += 1
            
            '''Industry Comparison'''
            
            '''Management and Equity'''
            if (ticker.OperationRatios.ROA.ThreeMonths) >= 0.05:
                rating += 1
                
            if (ticker.ValuationRatios.FCFRatio) >= 1:
                rating += 1
            
            '''Leverage and Liquidity'''
            if (ticker.OperationRatios.LongTermDebtTotalCapitalRatio.OneYear) <= 0.4:
                rating += 1
              
            '''Fundamental Variables'''
            if (ticker.ValuationRatios.PEGRatio) <= 1.0:
                rating += 1
                
            if (ticker.OperationRatios.ROE.ThreeMonths) >= 0.15:
                rating += 1
            
            '''Apply Rating'''
            self.ratingsDict[ticker.Symbol] = rating
            
        count = len(filteredFine)
        if count == 0: return []

        myDict = dict()
        percent = self.NumberOfSymbolsFine / count
     
        value3 = sorted(filteredFine, key = lambda x: self.ratingsDict[x.Symbol], reverse = True)
        value4 = value3[:ceil(len(value3) * percent)]
    
        self.stocks = value4[:self.NumberOfSymbolsInPortfolio]
    
        self.newstocks= [x.Symbol for x in self.stocks]
        
        algorithm.Debug(str([x.Value for x in self.newstocks]))
   
        return [x for x in self.newstocks ]