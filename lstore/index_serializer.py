import json
from lstore.btree import Btree, Node
from lstore.index import Index
from lstore.config import *

class IndexSerializer:

    def serialize_btree(btree: Btree) -> str:
        """
        Serializes a B-tree to a JSON string.
        """
        if not btree or not btree.root:
            return json.dumps(None)

        queue = [btree.root]
        serialized_nodes = []

        while queue:
            node = queue.pop(0)
            node_data = {
                "is_leaf": node.is_leaf,
                "keys": node.keys,
                "children": [] if node.is_leaf else [queue.index(child) for child in node.children]
            }
            serialized_nodes.append(node_data)

            if not node.is_leaf:
                queue.extend(node.children)

        return json.dumps(serialized_nodes)

    def deserialize_btree(data: str, t: int) -> Btree:
        """
        Deserializes a JSON string into a B-tree.
        """
        serialized_nodes = json.loads(data)
        if serialized_nodes is None:
            return None

        btree = Btree(t)
        nodes = [Node(is_leaf=node_data["is_leaf"], t=t) for node_data in serialized_nodes]

        for i, node_data in enumerate(serialized_nodes):
            nodes[i].keys = node_data["keys"]
            if not nodes[i].is_leaf:
                nodes[i].children = [nodes[j] for j in node_data["children"]]
        
        btree.root = nodes[0]  # Root is always first in BFS traversal
        return btree

    def serialize_index(index: Index) -> str:
        """
        Serializes the entire Index object, including all B-trees.
        """
        index_data = {
            "num_columns": len(index.indices),
            "indexed_columns": [i for i, tree in enumerate(index.indices) if tree],
            "btree_data": [IndexSerializer.serialize_btree(tree) if tree else None for tree in index.indices]
        }
        return json.dumps(index_data)

    def deserialize_index(data: str, table) -> Index:
        """
        Deserializes a JSON string into an Index object.
        """
        index_data = json.loads(data)
        index = Index(table)
        
        for column in index_data["indexed_columns"]:
            index.indices[column] = IndexSerializer.deserialize_btree(index_data["btree_data"][column], B_TREE_ORDER)

        return index
