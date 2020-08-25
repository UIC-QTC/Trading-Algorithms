# This program is entirely original work of Q.T.C. 
from QuantConnect.Data.UniverseSelection import * 
from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel 
from datetime import timedelta, datetime
from math import ceil
from itertools import chain
import numpy as np

class GreenBlattMagic(FundamentalUniverseSelectionModel):
    
    def __init__(self,
                 filterFineData = True,
                 universeSettings = None,
                 securityInitializer = None):
        '''Initializes a new default instance '''
        super().__init__(filterFineData, universeSettings, securityInitializer)

        # Number of stocks in Coarse Universe
        self.NumberOfSymbolsCoarse = 500
        # Number of sorted stocks in the fine selection subset using the valuation ratio, EV to EBITDA (EV/EBITDA)
        self.NumberOfSymbolsFine = 20
        # Final number of stocks in security list, after sorted by the valuation ratio, Return on Assets (ROA)
        self.NumberOfSymbolsInPortfolio = 10

        self.lastMonth = -1 
        self.dollarVolumeBySymbol = {} 

    def SelectCoarse(self, algorithm, coarse):
        
        #timestamp on last universe selection
        month = algorithm.Time.month
        if month == self.lastMonth:
            return Universe.Unchanged
        self.lastMonth = month
        
        # sort the stocks by dollar volume
        top = sorted([x for x in coarse if x.HasFundamentalData],
                    key=lambda x: x.DollarVolume, reverse=True)[:self.NumberOfSymbolsCoarse]

        self.dollarVolumeBySymbol = { i.Symbol: i.DollarVolume for i in top }
        #adds symbols and corresponding dollar volumne in dictionary
        
        return list(self.dollarVolumeBySymbol.keys())
      

    def SelectFine(self, algorithm, fine):

        # Below is the format to run a fine filter on our universe with below requirements
        ## The company's headquarter must in the U.S.
        ## The stock must be traded on either the NYSE or NASDAQ
        ## At least half a year since its initial public offering
        ## The stock's market cap must be greater than 500 million
        filteredFine = [x for x in fine if x.CompanyReference.CountryId == "USA"
                                        and (x.CompanyReference.PrimaryExchangeID == "NYS" or x.CompanyReference.PrimaryExchangeID == "NAS")
                                        and (algorithm.Time - x.SecurityReference.IPODate).days > 180
                                        and x.EarningReports.BasicAverageShares.ThreeMonths * x.EarningReports.BasicEPS.TwelveMonths * x.ValuationRatios.PERatio > 5e8]
        
        #if equities which meet requirements are empty return empty set
        count = len(filteredFine)
        if count == 0: return []

        #can create additional fine filters to further select our universe
        myDict = dict()
        percent = self.NumberOfSymbolsFine / count

        # select stocks with top dollar volume in every single sector
        # N=Normal (Manufacturing), M=Mining, U=Utility, T=Transportation, B=Bank, I=Insurance
        for key in ["N", "M", "U", "T", "B", "I"]:
            value = [x for x in filteredFine if x.CompanyReference.IndustryTemplateCode == key]
            value = sorted(value, key=lambda x: self.dollarVolumeBySymbol[x.Symbol], reverse = True)
            myDict[key] = value[:ceil(len(value) * percent)]
        
        # stocks in QC500 universe
        topFine = chain.from_iterable(myDict.values())

        #  Magic Formula:
        ## Rank stocks by Enterprise Value to EBITDA (EV/EBITDA)
        ## Rank subset of previously ranked stocks (EV/EBITDA), using the valuation ratio Return on Assets (ROA)
        # sort stocks in the security universe of QC500 based on Enterprise Value to EBITDA valuation ratio
        sortedByEVToEBITDA = sorted(topFine, key=lambda x: x.ValuationRatios.EVToEBITDA , reverse=True)

        # sort subset of stocks that have been sorted by Enterprise Value to EBITDA, based on the valuation ratio Return on Assets (ROA)
        sortedByROA = sorted(sortedByEVToEBITDA[:self.NumberOfSymbolsFine], key=lambda x: x.ValuationRatios.ForwardROA, reverse=False)

        # retrieve list of securites in portfolio
        return [f.Symbol for f in sortedByROA[:self.NumberOfSymbolsInPortfolio]]