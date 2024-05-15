from typing import List, Union

def format_dec(d):
    if d < 1e-4:
        return f'{d:.3e}'
    else:
        return f'{d:.4f}'

class ComputeClass:
    def __init__(self, name: str, cost: float):
        self.name = name
        self.cost = cost    # $ per second

    def calc_cost(self, time: int) -> float:
        return time * self.cost

    def __str__(self):
        return f'{self.name}, ${format_dec(self.cost)} per s'

    def __repr__(self):
        return f'{self.name}'
