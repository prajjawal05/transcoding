from bson import ObjectId
from typing import TypedDict, Dict, Type, Set, Union, List
from collections import deque

from ..storage import store

auth = ("23bc46b1-71f6-4ed5-8c54-816aa4f8c502",
        "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP")


class ObjectsInvolved(TypedDict):
    objects_read: Set[ObjectId]
    objects_written: Set[ObjectId]


class Node:
    def __init__(self, action_id=''):
        self.action_id: ObjectId = action_id
        self.objects_read: Set[str] = set()
        self.objects_written: Set[str] = set()
        self.children: Dict[ObjectId, Type['Node']] = dict()


class OrchestrationDAG:
    """
    This class is used to create the DAG (pointing from reader to writer for an object), and exposes other functions revolving around it.
    """

    def __init__(self) -> None:
        self.store = store.ObjectStore()
        self.memograph: Dict[str, Node] = dict()

    def get_node_prerequisite(self, action_id: ObjectId) -> List[ObjectId]:
        """
        This function gets the list of actions that writes the objects being read by the action_id.

        Parameters
        ----------
        action_id : ObjectId
            action id of the involved action.

        Returns
        -------
        List[ObjectId]
            The prerequisites of action id.

        """

        if not self.memograph:
            raise Exception('DAG not made')

        if str(action_id) not in self.memograph:
            raise Exception('Action not found in DAG')

        prereqs = self.memograph[str(action_id)].children.keys()

        return list(map(lambda action: ObjectId(action), prereqs))

    def construct_dag(self, orch_id: ObjectId) -> None:
        """
        This creates a DAG for an orch_id.

        Parameters
        ----------
        orch_id : ObjectId
            orch id of the involved orchestration.

        Returns
        -------
        None

        """
        objects_involved: ObjectsInvolved = self.store.get_objects_involved(
            orch_id)
        objects_never_read: Set[ObjectId] = objects_involved['objects_written'].difference(
            objects_involved['objects_read'])

        roots = []
        for object in objects_never_read:
            roots.append(self.__dfs(orch_id, object))

        # for root in roots:
        #     self.traverse(root)

    def __dfs(self, orch_id, object) -> Node:
        """
        This function runs a DFS to create a DAG of objects on the basis of object while storing the
        details of the graph in a dictionary.

        Parameters
        ----------
        orch_id : ObjectId
            orch id of the involved orchestration.

        object: str
            Name of the object whose creators we have to check.

        Returns
        -------
        Node:
            root of the current tree.

        """
        details = self.store.get_details_object_write(orch_id, object)
        if details is None:
            return None

        action_id = details['action_id']
        if action_id in self.memograph:
            return self.memograph[action_id]

        node = Node(action_id)
        for object_details in details.get('objects_put', []):
            node.objects_written.add(object_details['object'])
        for object_details in details.get('objects_get', []):
            node.objects_read.add(object_details['object'])
            child_node: Node = self.__dfs(orch_id, object_details['object'])
            if child_node is None:
                continue
            node.children[child_node.action_id] = child_node
        self.memograph[node.action_id] = node
        return node

    def traverse(self, root: Node) -> None:
        """
        This function is used to traverse a graph in a breadth first search fashion.

        Parameters
        ----------
        root: Node
            root of the tree where to start traversing

        Returns
        -------
        None

        """
        q = deque()
        q.append(root)
        q.append(None)

        while True:
            top: Union[Node, None] = q.popleft()

            if top is None:
                # print()
                if len(q) == 0:
                    return
                q.append(None)
                continue

            # print(top.action_id,
            #       "write:", top.objects_written, "read:", top.objects_read, end=" -- ")
            for childnode in top.children.values():
                if childnode in q:
                    continue
                q.append(childnode)


if __name__ == '__main__':
    predictor = OrchestrationDAG()
    predictor.construct_dag(ObjectId('6629d65467b8e9ef51118fe7'))
    # predictor.predict_runtime('video-transcoding', 'transcoder')
    # predictor.predict_runtime('video-transcoding', 'combiner')
