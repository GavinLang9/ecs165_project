from lstore.btree import Btree

"""
A data structure holding indices for various columns of a table. Key column should be indexed by default, other columns
can be indexed through this object. Indices are usually B-Trees, but other data structures can be used as well.
"""

B_TREE_ORDER = 3

class Index:

    def __init__(self, table):
        # One index for each table. All are empty initially.
        self.indices = [None] * table.num_columns

        # Index primary key column
        self.create_index( table.key )

    """
    # returns the location of all records with the given value on column "column"
    """

    def locate(self, column, value):
        # if column has not been created
        if self.indices[column] is None:
            return None

        result = self.indices[column].get( value )
        return result

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
