from typing import List, Union

class StorageClass:
    def __init__(self, name: str, cost: float, afr: float, cluster_size: int, bandwidth: float = None):
        self.name = name
        self.bw = bandwidth  # bytes per second
        self.cost = cost    # $ per GB-second
        self.afr = afr  # NOMDL_1h
        DISK_SIZE = 300 # disk size in GB
        self.cluster_size = cluster_size*1024*1024*1024*DISK_SIZE # cluster size in bytes

        #print(f'New storage class {self.name}: ${self.cost:.3e} $*s, AFR: {self.afr}')

    def time_to_process(self, size: int) -> float:
        return size / self.bw

    # lifetime in seconds
    # size in bytes
    def calc_cost(self, lifetime: int, size: int) -> float:
        return (size/1024/1024/1024) * lifetime * self.cost

    # lifetime in seconds
    # size in bytes
    # returns probability of failure during the lifetime of the data
    def prob_fail(self, lifetime: int, size: float) -> float:
        p = (self.afr/3600) * lifetime * (size/self.cluster_size)
        return p

    def __str__(self):
        return f'{self.name}'

    def __repr__(self):
        return f'{self.name}'

    def to_dict(self):
        return {'name': self.name, 'afr': self.afr, 'cost': self.cost, 'cluster_size': self.cluster_size}
