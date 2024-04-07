from bson import ObjectId
from BaseOrchestrator import BaseOrchestrator

auth = ("23bc46b1-71f6-4ed5-8c54-816aa4f8c502",
        "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP")


class OrchestratorCalculator:
    def __init__(self) -> None:
        self.orch = BaseOrchestrator(auth)

    def __get_details(self, orch_id):
        details = self.orch.get_orch_details(orch_id)
        print(details)
        return {
            'time_taken': details['time_taken'] + details['action_time_taken'],
            'data_stored': details['data_stored']
        }

    def compare(self, orch_id, compute_cost, object_cost):
        details = self.__get_details(orch_id)
        compute_charge = details['time_taken'] * compute_cost
        object_charge = details['data_stored'] * object_cost

        return 'compute' if compute_charge < object_charge else 'object'


if __name__ == '__main__':
    orch_calc = OrchestratorCalculator()
    print(orch_calc.compare('6612e2dea6890c1fbcb2d8d9', 1, 1))
    print(orch_calc.compare(ObjectId('6612e3b82f5107e3e9a236d5'), 1, 1))
