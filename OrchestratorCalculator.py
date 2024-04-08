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
        """
        This function compares the compute charge and storage charge and returns which option should be preferred
        for saving cost.

        Parameters
        ----------
        orch_id : ObjectId
            ID of Orchestration which is preferred

        compute_cost: number
            cost per time for the total computation

        object_cost: number
            cost per byte in storing the data used throughout.

        Returns
        -------
        str
            preferred option: compute or storage

        """
        details = self.__get_details(orch_id)
        compute_charge = details['time_taken'] * compute_cost
        storage_charge = details['data_stored'] * object_cost

        return 'compute' if compute_charge < storage_charge else 'storage'


if __name__ == '__main__':
    orch_calc = OrchestratorCalculator()
    print(orch_calc.compare('6612e2dea6890c1fbcb2d8d9', 1, 1))
    print(orch_calc.compare(ObjectId('6612e3b82f5107e3e9a236d5'), 1, 1))
