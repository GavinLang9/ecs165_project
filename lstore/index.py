from lstore.btree import Btree
import struct

"""
A data structure holding indices for various columns of a table. Key column should be indexed by default, other columns
can be indexed through this object. Indices are usually B-Trees, but other data structures can be used as well.
"""

B_TREE_ORDER = 3

class Index:

    def __init__(self, table):
        # One index for each table. All are empty initially.
        self.indices : list[Btree] = [None] * table.num_columns

        # Index primary key column
        self.create_index( table.key )

    def serialize(self):
        """
        Serializes all B-Trees in the `indices` list into a binary format.
        """
        serialized_b_tree_data = b""

        for btree in self.indices:
            if btree is None:
                serialized_b_tree_data += struct.pack("I", 0)  # No data for this index
            else:
                tree_data = btree.serialize()  # Use B-Tree's serialize method
                serialized_b_tree_data += struct.pack("I", len(tree_data))  # Store length
                serialized_b_tree_data += tree_data  # Store serialized B-Tree

        return serialized_b_tree_data
    
    @staticmethod
    def deserialize(index_binary_data, table):
        """
        Reconstructs the `Index` object from binary data.
        """
        index = Index(table)
        offset = 0

        for i in range(len(index.indices)):
            if offset >= len(index_binary_data):
                index.indices[i] = None  # Default to None if data is missing
                continue

            tree_size = struct.unpack_from("I", index_binary_data, offset)[0]
            offset += struct.calcsize("I")

            if tree_size == 0 or offset + tree_size > len(index_binary_data):
                index.indices[i] = None  # No index or corrupted data
            else:
                tree_data = index_binary_data[offset: offset + tree_size]
                offset += tree_size
                index.indices[i] = Btree.deserialize(tree_data)  # Deserialize B-tree

        return index

    """
    # returns the location of all records with the given value on column "column"
    """

    def locate(self, column, value):
        # if column has not been created
        if self.indices[column] is None:
            return None

        return self.indices[column].get( value )

    """
    # Returns the RIDs of all records with values in column "column" between "begin" and "end"
    """

    def locate_range(self, begin, end, column):
        # if column has not been created
        if self.indices[column] is None:
            return None

        return self.indices[ column ].get_range(begin, end)

    """
    # optional: Create index on specific column
    """

    def create_index(self, column_number):
        # exit if column index already exists
        if self.indices[column_number] is not None:
            return

        self.indices[column_number] = Btree(t=3)

    """
    # optional: Drop index of specific column
    """
    def drop_index(self, column_number):
        pass
