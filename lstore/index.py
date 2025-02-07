from lstore.btree import BTree

"""
A data structure holding indices for various columns of a table. Key column should be indexed by default, other columns
can be indexed through this object. Indices are usually B-Trees, but other data structures can be used as well.
"""


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

        result = self.indices[column].search( value )
        return result

    """
    # Returns the RIDs of all records with values in column "column" between "begin" and "end"
    """

    def locate_range(self, begin, end, column):
        # if column has not been created
        if self.indices[column] is None:
            return None

        key_val_pairs = self.indices[ column ].get_all_pairs()

        result_rids = []

        # find values in range
        for pair in key_val_pairs:
            if begin <= pair[0] <= end:
                # result_rids.append( self.indices[ column ].get( key ) )
                result_rids.append( pair[1] )

        return result_rids

    """
    # optional: Create index on specific column
    """

    def create_index(self, column_number):
        # exit if column index already exists
        if self.indices[column_number] is not None:
            return

        self.indices[column_number] = BTree()

    """
    # optional: Drop index of specific column
    """

    def drop_index(self, column_number):
        pass
