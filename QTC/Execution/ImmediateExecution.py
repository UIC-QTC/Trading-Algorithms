#This program was taken from QuantConnect's sample Execution modules 

class ImmediateExecutionModel(ExecutionModel):
    '''Provides an implementation of IExecutionModel that immediately submits market orders to achieve the desired portfolio targets'''

    def __init__(self):
        '''Initializes a new instance of the ImmediateExecutionModel class'''
        self.targetsCollection = PortfolioTargetCollection()

    def Execute(self, algorithm, targets):
        '''Immediately submits orders for the specified portfolio targets.
        Args:
            algorithm: The algorithm instance
            targets: The portfolio targets to be ordered'''

        # for performance we check count value, OrderByMarginImpact and ClearFulfilled are expensive to call
        self.targetsCollection.AddRange(targets)
        if self.targetsCollection.Count > 0:
            for target in self.targetsCollection.OrderByMarginImpact(algorithm):
                # calculate remaining quantity to be ordered
                quantity = OrderSizing.GetUnorderedQuantity(algorithm, target)
                if quantity != 0:
                    algorithm.MarketOrder(target.Symbol, quantity)

            self.targetsCollection.ClearFulfilled(algorithm)