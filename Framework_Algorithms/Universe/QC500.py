#This program was taken from QuantConnect's sample selection modules 

from QuantConnect.Data.UniverseSelection import *
from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel
from itertools import groupby
from math import ceil

class QC500UniverseSelectionModel(FundamentalUniverseSelectionModel):
    '''Defines the QC500 universe as a universe selection model for framework algorithm
    For details: https://github.com/QuantConnect/Lean/pull/1663'''

    def __init__(self, filterFineData = True, universeSettings = None, securityInitializer = None):
        '''Initializes a new default instance of the QC500UniverseSelectionModel'''
        super().__init__(filterFineData, universeSettings, securityInitializer)
        self.numberOfSymbolsCoarse = 1000
        self.numberOfSymbolsFine = 25
        self.dollarVolumeBySymbol = {}
        self.lastMonth = -1

    def SelectCoarse(self, algorithm, coarse):
        '''Performs coarse selection for the QC500 constituents.
        The stocks must have fundamental data
        The stock must have positive previous-day close price
        The stock must have positive volume on the previous trading day'''
        if algorithm.Time.month == self.lastMonth:
            return Universe.Unchanged

        sortedByDollarVolume = sorted([x for x in coarse if x.HasFundamentalData and x.Volume > 0 and x.Price > 0],
                                     key = lambda x: x.DollarVolume, reverse=True)[:self.numberOfSymbolsCoarse]

        self.dollarVolumeBySymbol = {x.Symbol:x.DollarVolume for x in sortedByDollarVolume}

        # If no security has met the QC500 criteria, the universe is unchanged.
        # A new selection will be attempted on the next trading day as self.lastMonth is not updated
        if len(self.dollarVolumeBySymbol) == 0:
            return Universe.Unchanged

        # return the symbol objects our sorted collection
        return list(self.dollarVolumeBySymbol.keys())

    def SelectFine(self, algorithm, fine):
        '''Performs fine selection for the QC500 constituents
        The company's headquarter must in the U.S.
        The stock must be traded on either the NYSE or NASDAQ
        At least half a year since its initial public offering
        The stock's market cap must be greater than 500 million'''

        sortedBySector = sorted([x for x in fine if x.CompanyReference.CountryId == "USA"
                                        and x.CompanyReference.PrimaryExchangeID in ["NYS","NAS"]
                                        and (algorithm.Time - x.SecurityReference.IPODate).days > 180
                                        and x.MarketCap > 5e8],
                               key = lambda x: x.CompanyReference.IndustryTemplateCode)

        count = len(sortedBySector)

        # If no security has met the QC500 criteria, the universe is unchanged.
        # A new selection will be attempted on the next trading day as self.lastMonth is not updated
        if count == 0:
            return Universe.Unchanged

        # Update self.lastMonth after all QC500 criteria checks passed
        self.lastMonth = algorithm.Time.month

        percent = self.numberOfSymbolsFine / count
        sortedByDollarVolume = []

        # select stocks with top dollar volume in every single sector
        for code, g in groupby(sortedBySector, lambda x: x.CompanyReference.IndustryTemplateCode):
            y = sorted(g, key = lambda x: self.dollarVolumeBySymbol[x.Symbol], reverse = True)
            c = ceil(len(y) * percent)
            sortedByDollarVolume.extend(y[:c])

        sortedByDollarVolume = sorted(sortedByDollarVolume, key = lambda x: self.dollarVolumeBySymbol[x.Symbol], reverse=True)
        algorithm.Debug(str([x.Symbol.Value for x in sortedByDollarVolume[:self.numberOfSymbolsFine]]))
        return [x.Symbol for x in sortedByDollarVolume[:self.numberOfSymbolsFine]]