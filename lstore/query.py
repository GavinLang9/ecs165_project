from lstore.table import Table, Record
from lstore.index import Index


class Query:
    """
    # Creates a Query object that can perform different queries on the specified table 
    Queries that fail must return False
    Queries that succeed should return the result or True
    Any query that crashes (due to exceptions) should return False
    """

    def __init__(self, table):
        self.table = table
        self.index = Index(table)
        pass

    """
    # Internal Method
    # Read a record with specified RID
    # Returns True upon successful deletion
    # Return False if record doesn't exist or is locked due to 2PL
    """

    def delete(self, primary_key):
        pass

    """
    # Insert a record with specified columns
    # Return True upon successful insertion
    # Returns False if insert fails for whatever reason
    """

    def insert(self, *columns):
        # Fail if mismatching number of columns
        if len(columns) != self.table.num_columns:
            return False

        primary_key = columns[ self.table.key ]

        # Fail if primary key already exists
        if self.index.locate(self.table.key, primary_key) is not None:
            return False

        # schema_encoding is part of the metadata columns.
        # metadata columns should include
            # indirection (base record points to latest tail record)
            # schema encoding
            # start time  (datetime?)
            # last update (initialize as None)
            # schema_encoding = '0' * self.table.num_columns

        # does create_record need the primary key?
        self.table.create_record( columns )

        # create index on primary key if needed
        # insert primary key into B-tree along with RID
        self.table.index.create_index(self.table.key)
        self.table.index.indices[self.table.key].insert( (primary_key, self.table.rid_counter) )

        # may need to implement checks, maybe in above function?
        return True

    """
    # Read matching record with specified search key
    # :param search_key: the value you want to search based on
    # :param search_key_index: the column index you want to search based on
    # :param projected_columns_index: what columns to return. array of 1 or 0 values.
    # Returns a list of Record objects upon success
    # Returns False if record locked by TPL
    # Assume that select will never be called on a key that doesn't exist
    """

    def select(self, search_key, search_key_index, projected_columns_index):
        # TODO : Fail if search_key_index is out of bounds

        # Fail if projected_columns_index does not match number of columns
        if len( projected_columns_index ) != self.table.num_columns:
            return False

        # get all RIDs of records that match search criteria
        rid_list = self.table.index.locate(search_key_index, search_key)

        # get all Record objects from rid_list
        record_list = []
        for rid in rid_list:
            record_list.append( self.table.get_record( rid ) )

        # apply projected_columns_index
        final_records = []
        for record in record_list:
            tmp_columns = tuple( column for column, include in zip( record.columns, projected_columns_index ) if include == 1 )
            final_records.append( Record( record.rid, record.key, tmp_columns ) )

        return final_records

    """
    # Read matching record with specified search key
    # :param search_key: the value you want to search based on
    # :param search_key_index: the column index you want to search based on
    # :param projected_columns_index: what columns to return. array of 1 or 0 values.
    # :param relative_version: the relative version of the record you need to retrieve.
    # Returns a list of Record objects upon success
    # Returns False if record locked by TPL
    # Assume that select will never be called on a key that doesn't exist
    
    relative_version: Assuming 0 is most recent tail record and relative_version decrements to iterate through
        previous tail records (versions)
    """

    def select_version(self, search_key, search_key_index, projected_columns_index, relative_version):
        # Get the record with version info
        rid = self.table.index.locate(search_key_index, search_key)
        if rid is None:
            return False
            
        if relative_version == 0:
            record = self.table.get_latest_record(rid)
        else:
            record = self.table.get_record(rid)
            
        if record is None:
            return False
        
    """
    # Update a record with specified key and columns
    # Returns True if update is successful
    # Returns False if no records exist with given key or if the target record cannot be accessed due to 2PL locking
    """

    def update(self, primary_key, *columns):
        # Fail if mismatching number of columns
        if len( columns ) != self.table.num_columns:
            return False

        # Fail if record does not exist
        rid = self.table.index.locate( self.table.key, primary_key )
        if rid == None:
            return False

        # TODO : update record
        # Update record and index
        self.table.update_record(rid, columns)
        self.table.indices[self.table.key].insert((primary_key, self.table.rid_counter))

        return True

    """
    :param start_range: int         # Start of the key range to aggregate 
    :param end_range: int           # End of the key range to aggregate 
    :param aggregate_columns: int  # Index of desired column to aggregate
    # this function is only called on the primary key.
    # Returns the summation of the given range upon success
    # Returns False if no record exists in the given range
    """

    def sum(self, start_range, end_range, aggregate_column_index):
        # Fail if start_range does not exist
        if self.table.index.locate( self.table.key, start_range ) == None:
            return False

        # TODO : Fail if aggregate_column_index is out of bounds

        # get all RIDs of records that match search criteria
        rid_list = self.table.index.locate_range( start_range, end_range, self.table.key )

        # get all Record objects from rid_list
        record_list = []
        for rid in rid_list:
            record_list.append(self.table.get_record(rid))

        # get summation from each record's aggregate_column_index
        summation = 0
        for record in record_list:
            summation += record.columns[ aggregate_column_index ]

        return summation


    """
    :param start_range: int         # Start of the key range to aggregate 
    :param end_range: int           # End of the key range to aggregate 
    :param aggregate_columns: int  # Index of desired column to aggregate
    :param relative_version: the relative version of the record you need to retrieve.
    # this function is only called on the primary key.
    # Returns the summation of the given range upon success
    # Returns False if no record exists in the given range
    
    relative_version: Assuming 0 is most recent tail record and relative_version decrements to iterate through
        previous tail records (versions)
    """

    def sum_version(self, start_range, end_range, aggregate_column_index, relative_version):
        # TODO : this entire function

        return self.sum( start_range, end_range, aggregate_column_index )

    """
    increments one column of the record
    this implementation should work if your select and update queries already work
    :param key: the primary of key of the record to increment
    :param column: the column to increment
    # Returns True is increment is successful
    # Returns False if no record matches key or if target record is locked by 2PL.
    """

    def increment(self, key, column):
        r = self.select(key, self.table.key, [1] * self.table.num_columns)[0]
        if r is not False:
            updated_columns = [None] * self.table.num_columns
            updated_columns[column] = r[column] + 1
            u = self.update(key, *updated_columns)
            return u
        return False