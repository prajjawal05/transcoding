from bson import ObjectId
from BaseOrchestrator import BaseOrchestrator
from InterpolatedPredictor import InterpolatedPredictor

from object_store import store
from constants import MONGO_HOST, MONGO_PORT

from typing import TypedDict, Union


class OrchestrationCostParameters(TypedDict):
    computeCharge: int
    orchestrationComputeCharge: int
    objectChargePerSizePerDuration: int


class ActionCostParameters(TypedDict):
    computeCharge: int
    objectChargePerSizePerDuration: int


class Cost(TypedDict):
    computeCost: int
    storageCost: int


class OrchDetails(TypedDict):
    timeTaken: int
    actionTimeTaken: int
    objectsCostCoefficient: int


class ActionDetails(TypedDict):
    timeTaken: int
    objectsCostCoefficient: int


auth = ("23bc46b1-71f6-4ed5-8c54-816aa4f8c502",
        "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP")


class OrchestratorCalculator:
    def __init__(self) -> None:
        self.orch = BaseOrchestrator(auth)
        self.predictor = InterpolatedPredictor()
        self.store = store.ObjectStore(
            db_config={'MONGO_HOST': MONGO_HOST, 'MONGO_PORT': MONGO_PORT})

    def __get_orch_cost_details(self, orch_id: ObjectId) -> OrchDetails:
        """
        This function gets the orchestrator details used for cost calculation. 

        Parameters
        ----------
        orch_id : ObjectId
            ID of orchestrator which is considered

        Returns
        -------
        OrchDetails
            returns the details used for cost calculation

        """
        details = self.orch.get_orch_details(orch_id)

        object_cost_coefficient = 0
        for metric in details['object_metrics']:
            object_cost_coefficient += metric['lifetime'] * \
                metric['size_written']

        return {
            'timeTaken': details['time_taken'],
            'actionTimeTaken': details['action_time_taken'],
            'objectsCostCoefficient': object_cost_coefficient
        }

    def __get_action_cost_details(self, action_id: ObjectId) -> ActionDetails:
        """
        This function gets the action details used for cost calculation. 

        Parameters
        ----------
        action_id : ObjectId
            ID of action which is considered

        Returns
        -------
        ActionDetails
            returns the details used for cost calculation

        """
        details = self.orch.get_action_details([action_id])[action_id]

        object_cost_coefficient = 0
        for metric in details['objects'].values():
            object_cost_coefficient += metric['lifetime'] * \
                metric['size']

        return {
            'timeTaken': details['runtime'],
            'objectsCostCoefficient': object_cost_coefficient
        }

    def get_orch_cost_by_name(self, orch_name: str, cost: OrchestrationCostParameters) -> Cost:
        """
        This function calculates the average compute cost and average storage cost for running an orchestrator. 

        Parameters
        ----------
        orch_name : str
            name of orchestrator which is considered

        cost: OrchestrationCostParameters
            the various parameters used in cost calculation

        Returns
        -------
        Cost
            returns the cost of running the orchestrator

        """

        orch_ids = self.orch.get_all_orchs(orch_name)
        total_compute_cost = 0
        total_storage_cost = 0
        for orch_id in orch_ids:
            instance_cost: Cost = self.get_orch_cost_by_id(orch_id, cost)
            total_compute_cost = total_compute_cost + \
                instance_cost['computeCost']
            total_storage_cost = total_storage_cost + \
                instance_cost['storageCost']

        avg_compute_cost = total_compute_cost / len(orch_ids)
        avg_storage_cost = total_storage_cost / len(orch_ids)

        return {
            'computeCost': avg_compute_cost,
            'storageCost': avg_storage_cost
        }

    def get_orch_cost_by_id(self, orch_id: Union[int, ObjectId], cost: OrchestrationCostParameters) -> Cost:
        """
        This function calculates the compute cost and storage cost for running an orchestrator. 

        Parameters
        ----------
        orch_id : Union[int, ObjectId]
            ID of orchestrator which is considered

        cost: OrchestrationCostParameters
            the various parameters used in cost calculation

        Returns
        -------
        Cost
            returns the cost of running the orchestrator

        """
        details = self.__get_orch_cost_details(orch_id)
        compute_charge = details['actionTimeTaken'] * cost['computeCharge'] + \
            details['timeTaken'] * cost['orchestrationComputeCharge']
        storage_charge = details['objectsCostCoefficient'] * \
            cost['objectChargePerSizePerDuration']

        return {
            'computeCost': compute_charge,
            'storageCost': storage_charge,
        }

    def get_action_cost_by_name(self, action_name: str, cost: ActionCostParameters) -> Cost:
        """
        This function calculates the average compute cost and average storage cost for running an action. If there are retries,
        it would take an average.

        Parameters
        ----------
        action_name : str
            name of action which is considered

        cost: ActionCostParameters
            the various parameters used in cost calculation

        Returns
        -------
        Cost
            returns the cost of running the action

        """

        # lifetime
        # orch_name
        # expose three functions
        action_ids = self.orch.get_all_actions_for_id(action_name)
        total_compute_cost = 0
        total_storage_cost = 0
        for action_id in action_ids:
            instance_cost: Cost = self.get_action_cost_by_id(action_id, cost)
            total_compute_cost = total_compute_cost + \
                instance_cost['computeCost']
            total_storage_cost = total_storage_cost + \
                instance_cost['storageCost']

        avg_compute_cost = total_compute_cost / len(action_ids)
        avg_storage_cost = total_storage_cost / len(action_ids)

        return {
            'computeCost': avg_compute_cost,
            'storageCost': avg_storage_cost
        }

    def get_action_cost_by_id(self, action_id: Union[int, ObjectId], cost: ActionCostParameters) -> Cost:
        """
        This function calculates the compute cost and storage cost for running an action. If there are retries,
        it would take an average.

        Parameters
        ----------
        action_id : Union[int, ObjectId]
            ID of action which is considered

        cost: ActionCostParameters
            the various parameters used in cost calculation

        Returns
        -------
        Cost
            returns the cost of running the action

        """
        if not isinstance(action_id, ObjectId):
            action_id = ObjectId(action_id)

        details = self.__get_action_cost_details(action_id)
        compute_charge = details['timeTaken'] * cost['computeCharge']
        storage_charge = details['objectsCostCoefficient'] * \
            cost['objectChargePerSizePerDuration']

        return {
            'computeCost': compute_charge,
            'storageCost': storage_charge,
        }

    def predict_action_cost(self, orch_name, action_name, cost: ActionCostParameters, input_size):
        def _get_objects_written():
            action_id = self.orch.get_all_actions_for_id(action_name)[-1]
            action_details = self.store.get_action_details(action_id)
            return list(map(
                lambda object_put: object_put['object'], action_details.get('objects_put', [])))

        objects_written = _get_objects_written()

        action_runtime = self.predictor.predict_runtime(
            orch_name, action_name, input_size)

        objects_cost_coefficient = 0
        for object in objects_written:
            lifetime = self.predictor.predict_lifetime(
                orch_name, action_name, input_size, object)
            size = self.predictor.predict_size(
                orch_name, action_name, input_size, object)
            objects_cost_coefficient += lifetime * size

        compute_charge = cost['computeCharge'] * action_runtime
        storage_charge = cost['objectChargePerSizePerDuration'] * \
            objects_cost_coefficient

        return {
            'computeCost': compute_charge,
            'storageCost': storage_charge,
        }


if __name__ == '__main__':
    orch_calc = OrchestratorCalculator()

    #  Orchestration Cost
    # cost = OrchestrationCostParameters(
    #     computeCharge=1, orchestrationComputeCharge=0.5, objectChargePerSizePerDuration=2)
    # print(orch_calc.get_orch_cost_by_id('661c42df67a34ef406610e96', cost))
    # print(orch_calc.get_orch_cost_by_id(
    #     ObjectId('661c43ce6e85eda27393bf4c'), cost))
    # print(orch_calc.get_orch_cost_by_name('chatbot', cost))

    #  Action Cost
    action_cost = ActionCostParameters(
        computeCharge=1, objectChargePerSizePerDuration=2)
    # print(orch_calc.get_action_cost_by_id(
    #     '6629b51ac1ebc577b2e566b4', action_cost))
    # print(orch_calc.get_action_cost_by_id(
    #     ObjectId('661c43d66e85eda27393bf62'), action_cost))
    # print(orch_calc.get_action_cost_by_name('split-action', action_cost))

    orch_calc.predict_action_cost('video-transcoding', 'splitter', action_cost,
                                  2389332)
