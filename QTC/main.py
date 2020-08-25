#Here is our main file that runs everything, individual modules for each framework can be found in the corresponding folder 
from Universe import SampleUniverse2, QC500,UncorrelatedUniverseSelection, FundamentalUniverse
from Alpha import Volatility, SentimentMean, SampleAlpha, SECInvestor, ProbabilisticMomentum, BasePairsTrading
from PortfolioConstruction import EqualWeighting
from RiskManagement import MaxDrawdown, TrailingStop
from Execution import ImmediateExecution, StandardDeviation, VWAP

from datetime import date, timedelta

class test (QCAlgorithm):
    
    def Initialize(self):
        self.SetStartDate(2019,7,25)  
        self.SetEndDate(2020,7, 25)
        self.SetCash(1000000)  # Set Strategy Cash
        self.SetTimeZone(TimeZones.Chicago)
        
        self.AddUniverseSelection(FundamentalUniverse.universe())
        
        self.UniverseSettings.Resolution = Resolution.Minute #Sets resolution to minute
        self.UniverseSettings.DataNormalizationMode=DataNormalizationMode.Raw #how data goes into alg
        self.UniverseSettings.FillForward = True #Fill in empty data will next price
        self.UniverseSettings.ExtendedMarketHours = False #Takes in account after hours data
        self.UniverseSettings.MinimumTimeInUniverse = 1 # each equity has to spend at least 1 hour in universe selection process
        self.UniverseSettings.Leverage=2
        
        # We want to rebalance only on security changes
        self.Settings.RebalancePortfolioOnInsightChanges = False;
        self.Settings.RebalancePortfolioOnSecurityChanges = True;
       
        # Sets the amount of free cash in our portfolio
        self.Settings.FreePortfolioValuePercentage = 0.5
        
        self.SetBenchmark("SPY")
       
        self.AddAlpha(Volatility.MACDTrendAlgorithm())
        
        self.SetPortfolioConstruction(EqualWeighting.EqualWeightingPortfolioConstructionModel())
        self.SetRiskManagement(TrailingStop.TrailingStopRiskManagementModel(0.03))
        self.SetExecution(VWAP.VolumeWeightedAveragePriceExecutionModel())