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
        if len(columns) != self.table.num_columns:
            return False

        primary_key = columns[self.table.key]
        # First check if key exists
        if self.index.locate(self.table.key, primary_key) is not None:
            return False

        # Create record
        self.table.create_record(columns)
        rid = self.table.rid_counter - 1  # Get RID of just created record

        # Create index and insert
        self.index.create_index(self.table.key)
        self.index.indices[self.table.key].insert((primary_key, rid))

        return True
        
        print(f"Inserting key {primary_key} with RID {rid}")

    """
    # Read matching record with specified search key
    # :param search_key: the value you want to search based on
    # :param search_key_index: the column index you want to search based on
    # :param projected_columns_index: what columns to return. array of 1 or 0 values.
    # Returns a list of Record objects upon success
    # Returns False if record locked by TPL
    # Assume that select will never be called on a key that doesn't exist
    """

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
        # Fail if search_key_index is out of bounds
        if search_key_index < 0 or search_key_index >= self.table.num_columns:
            return False

        # Fail if projected_columns_index does not match number of columns
        if len( projected_columns_index ) != self.table.num_columns:
            return False

        # get all RIDs of records that match search criteria
        rid_list = self.index.locate(search_key_index, search_key)

        # get all Record objects from rid_list
        record_list = []
        for rid in rid_list:
            record_list.append( self.table.get_latest_record( rid ) )

        # apply projected_columns_index
        final_records = []
        for record in record_list:
            tmp_columns = tuple( column for column, include in zip( list(record.columns), projected_columns_index ) if include == 1 )
            final_records.append( Record( record.rid, record.indirection, record.key, tmp_columns ) )

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
        if relative_version > 0:
            raise ValueError("Invalid relative version")

        # Get the base RIDs with the search key
        rid = self.index.locate(search_key_index, search_key)
        if rid is None:
            return False
        rid_list = [rid]  # Convert single RID to list

        # Get latest records for the base RIDs
        latest_record_list = [self.table.get_latest_record(rid) for rid in rid_list]

        if relative_version == 0:  # Fetch the latest version
            return latest_record_list

        final_records = []
        for record in latest_record_list:
            base_rid = record.rid
            current_record = record  # Start from the latest record
        
            # Traverse backwards through previous versions
            for step in range(abs(relative_version)):  
                
                if current_record.indirection is None or current_record.indirection == base_rid:  
                    break  # Stop if no more history exists
                
                previous_record = self.table.get_record(current_record.indirection)
                
                if previous_record is None:
                    break  # Stop if we reached a dead end
                
                current_record = previous_record  # Move to the older version

            # Apply column projection
            tmp_columns = tuple(column for column, include in zip(list(current_record.columns), projected_columns_index) if include == 1)
            final_records.append(Record(current_record.rid, current_record.indirection, current_record.key, tmp_columns))

        return final_records
        
    """
    # Update a record with specified key and columns
    # Returns True if update is successful
    # Returns False if no records exist with given key or if the target record cannot be accessed due to 2PL locking
    """

    def update(self, primary_key, *columns):
        if len(columns) != self.table.num_columns:
            return False

        primary_key_column_idx = self.table.key
        rid = self.index.locate(primary_key_column_idx, primary_key)
        if rid is None:
            return False
        
        # Create indices for all columns first
        for col_index in range(self.table.num_columns):
            self.index.create_index(col_index)
            
        old_record = self.table.get_record(rid)
        self.table.update_record(rid, list(columns))

        # Update B+ tree index for each column that changed
        for col_index, new_value in enumerate(columns):

            if new_value is None:  # Skip if no update for this column
                continue
                
            old_value = old_record.columns[col_index]
            
            old_rid_set = self.index.indices[col_index].get(old_value)
            if old_rid_set and rid in old_rid_set:
                old_rid_set.remove(rid)
                if not old_rid_set:
                    try:
                        self.index.indices[col_index].remove(old_value)
                    except:
                        pass  

            # Inserting new value
            new_rid_set = self.index.indices[col_index].get(new_value)
            if new_rid_set is not None:
                new_rid_set.add(rid)
            else:
                self.index.indices[col_index].insert((new_value, {rid}))

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
       
        # Get all records in range
        rid_list = self.table.index.indices[self.table.key].get_range(start_range, end_range)
        if not rid_list:
            return 0 
            
        summation = 0
        for rid in rid_list:
            try:
                if relative_version == 0:
                    record = self.table.get_latest_record(rid)
                else:
                    record = self.table.get_record(rid)
                    current_record = record

                    for _ in range(abs(relative_version) - 1):
                        if current_record.indirection == current_record.rid:
                            break
                        next_record = self.table.get_record(current_record.indirection)
                        if not next_record:
                            break
                        current_record = next_record
                    record = current_record

                if record and aggregate_column_index < len(record.columns):
                    value = record.columns[aggregate_column_index]
                    if value is not None:
                        summation += value
            except Exception as e:
                continue

        return summation
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
