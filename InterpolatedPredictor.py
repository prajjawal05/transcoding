from bson import ObjectId
from BaseOrchestrator import BaseOrchestrator

from typing import TypedDict, Union
from numpy import interp


auth = ("23bc46b1-71f6-4ed5-8c54-816aa4f8c502",
        "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP")


def reorder_arrays(X, Y):
    """
        This function rearranges X and Y in a way that X is sorted in an increasing order and 
        the pair {X[i], Y[i]} remains the same after the sort. 

        Parameters
        ----------
        X : List[Any]
            Primary list

        Y : List[Any]
            Secondary list

        Returns
        -------
        List[Any], List[Any]
            Inputs but in sorted order

    """
    index_mapping = sorted(range(len(X)), key=lambda i: X[i])
    X_sorted = [X[i] for i in index_mapping]
    Y_sorted = [Y[i] for i in index_mapping]

    return X_sorted, Y_sorted


class InterpolatedPredictor:
    def __init__(self) -> None:
        self.orch = BaseOrchestrator(auth)

    def __fetch_all_details(self, orch_name, action_name):
        """
        This function gets action runtime details and the object details for each action and orch.

        Parameters
        ----------
        orch_name : str
            Name of the orchestrator

        action_name : str
            Name of the action

        Returns
        -------
        dict[ObjectId, dict[ObjectId, dict]]
            Inputs but in sorted order

        """
        orch_ids = self.orch.get_all_orchs(orch_name)
        action_ids = self.orch.get_all_actions_for_id(action_name)
        details = self.orch.get_action_details(action_ids, orch_ids)
        return details

    def predict_runtime(self, orch_name, action_name, input_size=0):
        """
        This function predicts the runtime of an action within an orch for different input size using interpolation.

        Parameters
        ----------
        orch_name : str
            Name of the orchestrator

        action_name : str
            Name of the action

        input_size : int
            Size of the input to the orchestration

        Returns
        -------
        float
            The predicted runtime

        """
        details = self.__fetch_all_details(orch_name, action_name)
        input_size_X = []
        runtime_Y = []
        for orch_id, orch_action_details in details.items():
            input_size = self.orch.get_orch_details(orch_id)['input_size']
            for action_metrics in orch_action_details.values():
                runtime = action_metrics['runtime']
                input_size_X.append(input_size)
                runtime_Y.append(runtime)

        X, Y = reorder_arrays(input_size_X, runtime_Y)
        predicted_runtime = interp(x=input_size, xp=X, fp=Y)
        return predicted_runtime

    def predict_size(self, orch_name, action_name, input_size, object_name=''):
        """
        This function predicts the size of a particular object created by an action within an orch 
        for different input size using interpolation.

        Parameters
        ----------
        orch_name : str
            Name of the orchestrator

        action_name : str
            Name of the action

        input_size : int
            Size of the input to the orchestration

        object_name: str
            Object to predict the size for

        Returns
        -------
        float
            The predicted size

        """
        details = self.__fetch_all_details(orch_name, action_name)
        input_size_X = []
        object_size_Y = []
        for orch_id, orch_action_details in details.items():
            input_size = self.orch.get_orch_details(orch_id)['input_size']
            for action_metrics in orch_action_details.values():
                if object_name not in action_metrics['objects']:
                    continue
                object_size = action_metrics['objects'][object_name]['size']
                input_size_X.append(input_size)
                object_size_Y.append(object_size)

        X, Y = reorder_arrays(input_size_X, object_size_Y)
        predicted_size = interp(x=input_size, xp=X, fp=Y)

        return predicted_size

    def predict_lifetime(self, orch_name, action_name, input_size, object_name=''):
        """
        This function predicts the size of a particular object created by an action within an orch 
        for different input size using interpolation.

        Parameters
        ----------
        orch_name : str
            Name of the orchestrator

        action_name : str
            Name of the action

        input_size : int
            Size of the input to the orchestration

        object_name: str
            Object to predict the size for

        Returns
        -------
        float
            The predicted size

        """
        details = self.__fetch_all_details(orch_name, action_name)
        input_size_X = []
        object_lifetime_Y = []
        for orch_id, orch_action_details in details.items():
            input_size = self.orch.get_orch_details(orch_id)['input_size']
            for action_metrics in orch_action_details.values():
                if object_name not in action_metrics['objects']:
                    continue
                object_size = action_metrics['objects'][object_name]['lifetime']
                input_size_X.append(input_size)
                object_lifetime_Y.append(object_size)

        X, Y = reorder_arrays(input_size_X, object_lifetime_Y)
        predicted_lifetime = interp(x=input_size, xp=X, fp=Y)
        return predicted_lifetime


if __name__ == '__main__':
    predictor = InterpolatedPredictor()
    predictor.predict_lifetime('video-transcoding', 'splitter',
                               2389332, 'output-chunks/chunk_0_1714017881.mp4')
    # predictor.predict_runtime('video-transcoding', 'transcoder')
    # predictor.predict_runtime('video-transcoding', 'combiner')
