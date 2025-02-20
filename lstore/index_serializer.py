import json
import pdb
from lstore.btree import Btree, Node
from lstore.index import Index
from lstore.config import *

class IndexSerializer:

    def serialize_btree(btree: Btree) -> str:
        """
        Serializes a B-tree into a JSON string.
        """
        if btree.root is None:
            return json.dumps([])  # Return an empty JSON list for an empty tree

        queue = [btree.root]
        node_to_index = {btree.root: 0}  # Track unique node indices
        serialized_nodes = []

        while queue:
            node = queue.pop(0)
            node_index = node_to_index[node]

            serialized_nodes.append({
                "is_leaf": node.is_leaf,
                "keys": [{"key": key, "rids": rids} for key, rids in node.keys],  # Store as dictionary
                "children": []
            })

            if not node.is_leaf:
                for child in node.children:
                    if child not in node_to_index:
                        node_to_index[child] = len(node_to_index)
                        queue.append(child)
                    serialized_nodes[node_index]["children"].append(node_to_index[child])

        return serialized_nodes # Use indent=2 for readability


    def deserialize_btree(data, t: int) -> Btree:
        """
        Deserializes a JSON string into a B-tree.
        """
        serialized_nodes = data
        if not serialized_nodes:
            return Btree(t)  # Return an empty tree if there's no data

        btree = Btree(t)
        nodes = [Node(is_leaf=node_data["is_leaf"], t=t) for node_data in serialized_nodes]

        # Assign keys correctly
        for i, node_data in enumerate(serialized_nodes):
            nodes[i].keys = [(key_data["key"], key_data["rids"]) for key_data in node_data["keys"]]  # Proper format

        # Assign children (only after all nodes are created)
        for i, node_data in enumerate(serialized_nodes):
            if not nodes[i].is_leaf:
                nodes[i].children = [nodes[j] for j in node_data["children"] if j < len(nodes)]

        btree.root = nodes[0] if nodes else None  # Avoid accessing empty list
        return btree

    def serialize_index(index: Index):
        """
        Serializes the entire Index object, including all B-trees into json
        """
        index_data = {
            "num_columns": len(index.indices),
            "indexed_columns": [i for i, tree in enumerate(index.indices) if tree],
            "btree_data": [IndexSerializer.serialize_btree(tree) if tree else None for tree in index.indices]
        }
        return index_data

    def deserialize_index(index_data, table) -> Index:
        """
        Deserializes a JSON string into an Index object.
        """
        
        index = Index(table)
        
        for column in index_data["indexed_columns"]:
            index.indices[column] = IndexSerializer.deserialize_btree(index_data["btree_data"][column], B_TREE_ORDER)

        return index
