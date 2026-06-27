class ResourceManager:
    def __init__(self, max_cost=0.10):
        self.max_cost = max_cost
        self.spent = 0.0

    def can_afford(self, cost_estimate):
        return self.spent + cost_estimate <= self.max_cost

    def spend(self, actual_cost):
        self.spent += actual_cost
