from typing import Tuple
from lstore.index import Index
from lstore.bufferpool import BufferPool
from lstore.disk import Disk
from lstore.page import Page
from time import time

INDIRECTION_COLUMN = 0
RID_COLUMN = 1
TIMESTAMP_COLUMN = 2
SCHEMA_ENCODING_COLUMN = 3

BUFFER_POOL_CAPACITY = 16
RECORDS_PER_PAGE = 512
PAGE_RANGE_MAX_LEN = 64
NUM_META_COLUMNS = 4

class Record:

    def __init__(self, rid, key, columns):
        self.rid = rid
        self.key = key
        self.columns = columns

class Table:

    """
    :param name: string         #Table name
    :param num_columns: int     #Number of Columns: all columns are integer
    :param key: int             #Index of table key in columns
    """
    def __init__(self, name, num_columns, key):
        self.name = name
        self.key = key
        self.num_columns = num_columns
        self.page_directory = {}    # RID -> ([page_range_ids], [page_ids], [offsets])
        self.disk = Disk()
        self.bufferpool = BufferPool(BUFFER_POOL_CAPACITY, self.disk)
        self.index = Index(self)
        self.rid_counter = 0

        # base page data
        self.current_base_page_range = 0
        self.current_base_page = 0   # page id of first column page
        self.current_base_offset = 0
        # tail page data
        self.current_tail_page_range = 0
        self.current_tail_page = 0
        self.current_tail_offset = 0
        pass

    def create_record(self, columns):
        """
        Creates a new record by writing columns to their corresponding pages.
        
        Args:
            key (int): Primary key value
            columns (list[int]): List of column values to write
                first column is key column (usually)
                [key, col 1, col 2, col 3, ...]
        """
        # create meta data columns
        if len(columns) != self.num_columns:  
            raise ValueError("Invalid number of columns")
        rid = self.rid_counter
        metadata = [
            rid,                            # INDIRECTION
            rid,                            # RID
            int(time() * 1000),             # TIMESTAMP
            [0] * len( columns )            # SCHEMA ENCODING
        ]
        record_data = metadata + list( columns )

        # returns a tuple of lists that hold page range and page indexes for each column
        page_range_ids, column_page_ids = self._get_base_write_locations()

        offsets = []
        # write each column to their corresponding location in disk

        for value, page_range_id, page_id in zip(record_data, page_range_ids, column_page_ids):
            page = self.bufferpool.get_page(page_range_id, page_id)

            if not page:
                page = Page()
                
            if not page.has_capacity():
                raise IndexError("This page has no space")

            index = page.write(value)
            offsets.append(index)
            self.bufferpool.write_page(page_range_id, page_id, page)
        # Update table metadata
        self.page_directory[rid] = (page_range_ids, column_page_ids, offsets)
        self._update_base_indexes()

    def update_record(self, primary_key, columns):
        """
        Updates a record by writing columns to their corresponding tail pages
        and updating the base record indirection and schema encoding.

        Args:
            primary_key (int): Primary key value
            columns (tuple): List of column values to write
                first column is key column (usually)
                [key, col 1, col 2, col 3, ...]
        """

        # Fails if record with PK does not already exist
        base_rid = self.index.locate( self.key, primary_key )
        if base_rid == None:
            return False

        latest_record = self.get_latest_record( base_rid )

        # create meta data columns
        if len(columns) != self.num_columns:
            raise ValueError("Invalid number of columns")

        rid = self.rid_counter
        schema_encoding = self._get_schema_encoding( columns )

        metadata = [
            latest_record.rid,                          # INDIRECTION (previous tail record's RID)
            rid,                                        # RID
            int(time() * 1000),                         # TIMESTAMP
            schema_encoding                             # SCHEMA ENCODING
        ]
        record_data = metadata + list( self._get_cumulative_tail_record_columns( latest_record, columns ) )

        # returns a tuple of lists that hold page range and page indexes for each column
        page_range_ids, column_page_ids = self._get_tail_write_locations()

        offsets = []

        # write each column to their corresponding location in disk
        for value, page_range_id, page_id in zip(record_data, page_range_ids, column_page_ids):
            page = self.bufferpool.get_page(page_range_id, page_id)

            if not page:
                page = Page()

            if not page.has_capacity():
                raise IndexError("This page has no space")

            index = page.write(value)
            offsets.append(index)
            self.bufferpool.write_page(page_range_id, page_id, page)
        # Update table metadata
        self.page_directory[rid] = (page_range_ids, column_page_ids, offsets)
        self._update_tail_indexes()

        # TODO : update base record metadata
        self._update_base_record_metadata( base_rid, rid, schema_encoding )


    def get_latest_record(self, base_rid: int) -> Record:
        """
        Gets the most recent version of the record and
        returns constructed record by getting each column value from their respective pages
        :param rid: base record RID

        Note: base record indirection is latest tail record RID,
              tail record indirection is previous tail record RID
        """
        record = self.get_record( base_rid )

        # return record if indirection is RID
        # AKA return record if it is the base record (has no updates)
        if record.columns[0] == record.rid:
            return record

        latest_tail_record = self.get_record( record.columns[0] )

        # Avoids fully populating the values from the base record into all tail pages
        if latest_tail_record.columns[0] == record.rid:
            return latest_tail_record

        # Using cumulative tail records
        for col_idx in range(NUM_META_COLUMNS + self.num_columns):
            if latest_tail_record.columns[ col_idx ] is None:
                latest_tail_record.columns[ col_idx ] = record.columns[ col_idx ]

        return latest_tail_record

    def _get_schema_encoding(self, columns):
        """
        Takes a tuple of column values and returns a bitmap (list) for new schema encoding

        :param columns: tuple of values
        """
        new_schema_encoding = []

        for val in columns:
            if val is None:
                new_schema_encoding.append(0)
            else:
                new_schema_encoding.append(1)

        return new_schema_encoding

    def _get_cumulative_tail_record_columns(self, latest_record: Record, columns: tuple):
        """
        Returns the cumulative tail based off of previous tail record and new columns values

        :param latest_record: Record object, most recent tail record
        :param columns: tuple of values
        """
        # keep columns as-is if latest_record is tail record
        if latest_record.rid == latest_record.columns[0]:
            return columns

        # update new columns to be cumulative of previous tail record column values
        for col_idx in range( self.num_columns ):
            if latest_record.columns[ 4 + col_idx ] != columns[ col_idx ]:
                columns[ col_idx ] = latest_record.columns[ 4 + col_idx ]

        return columns

    def _update_base_record_metadata(self, base_rid, new_rid, schema_encoding):
        base_record = self.get_record( base_rid )

        base_record.columns[0] = new_rid
        base_record.columns[3] = schema_encoding

        # TODO : write new metadata back to original base record page


    def get_record(self, rid: int) -> Record:
        """
        returns constructed record by getting each column value from their respective pages
        """
        page_range_ids, page_ids, offsets = self.page_directory[rid]
        columns = []
        for page_range_id, page_id, offset in zip(page_range_ids, page_ids, offsets):
            page = self.bufferpool.get_page(page_range_id, page_id)
            value = page[offset]
            columns.append(value)
        record = Record(rid, columns[self.key + NUM_META_COLUMNS], columns[5:]) # 4 columns of metadata followed by key
        return record

    def _new_pages_will_overflow_page_range(self, current_page, total_columns):
        """
        Checks if writing new pages would exceed the current page range capacity.
        
        Args:
            total_columns (int): Number of columns to be written
            
        Returns:
            bool: True if writing would overflow the current page range
        """
        return current_page + total_columns > PAGE_RANGE_MAX_LEN

    def _get_base_write_locations(self) -> Tuple[list[int], list[int]]:
        """
        Determines the page range and page index for each column to be written.
        
        Returns:
            tuple: Contains two lists:
                - List of page_range_ids for each column
                - List of page_ids for each column
        """
        # Default all columns will be written to self.current_base_page_range
        total_columns = self.num_columns + NUM_META_COLUMNS
        page_range_ids = [self.current_base_page_range] * total_columns
        column_page_ids = list(range(self.current_base_page, self.current_base_page + total_columns))
        
        # If no overflow, all columns go to current page range
        if not self._new_pages_will_overflow_page_range( self.current_base_page, total_columns ):
            return (page_range_ids, column_page_ids)

        # Else, split columns into remaining space and next page range
        remaining_space = PAGE_RANGE_MAX_LEN - self.current_base_page # number of columns that will be stored in current page
        overflow_columns = total_columns - remaining_space

        page_range_ids = (
                [self.current_base_page_range] * remaining_space +
                [self.current_base_page_range + 1] * overflow_columns
        )

        column_page_ids = (
                list(range(self.current_base_page, PAGE_RANGE_MAX_LEN)) +
                list(range(overflow_columns))
        )
        return (page_range_ids, column_page_ids)

    def _get_tail_write_locations(self) -> Tuple[list[int], list[int]]:
        """
        Determines the page range and page index for each column to be written.

        Returns:
            tuple: Contains two lists:
                - List of page_range_ids for each column
                - List of page_ids for each column
        """
        # Default all columns will be written to self.current_tail_page_range
        total_columns = self.num_columns + NUM_META_COLUMNS
        page_range_ids = [self.current_tail_page_range] * total_columns
        column_page_ids = list(range(self.current_tail_page, self.current_tail_page + total_columns))

        # If no overflow, all columns go to current page range
        if not self._new_pages_will_overflow_page_range( self.current_tail_page, total_columns ):
            return (page_range_ids, column_page_ids)

        # Else, split columns into remaining space and next page range
        remaining_space = PAGE_RANGE_MAX_LEN - self.current_tail_page  # number of columns that will be stored in current page
        overflow_columns = total_columns - remaining_space

        page_range_ids = (
                [self.current_tail_page_range] * remaining_space +
                [self.current_tail_page_range + 1] * overflow_columns
        )

        column_page_ids = (
                list(range(self.current_tail_page, PAGE_RANGE_MAX_LEN)) +
                list(range(overflow_columns))
        )
        return (page_range_ids, column_page_ids)

    def _update_base_indexes(self):
        """
        Update table counters for  
            page range  
            page id  
            offset
            rid  
        """
        total_columns = self.num_columns + NUM_META_COLUMNS

        if self._page_is_full( self.current_base_offset ) and self.current_base_offset != 0:
            if self._page_range_is_full(self.current_base_page, total_columns):
                self.current_base_page_range += 1
            new_page_id = (self.current_base_page + total_columns) % PAGE_RANGE_MAX_LEN
            self.current_base_page = new_page_id
            self.current_base_offset = 0
        self.rid_counter += 1
        self.current_base_offset += 1

    def _update_tail_indexes(self):
        """
        Update table counters for
            page range
            page id
            offset
            rid
        """
        total_columns = self.num_columns + NUM_META_COLUMNS

        if self._page_is_full( self.current_tail_offset ) and self.current_tail_offset != 0:
            if self._page_range_is_full( self.current_tail_page, total_columns ):
                self.current_tail_page_range += 1
            new_page_id = (self.current_tail_page + total_columns) % PAGE_RANGE_MAX_LEN
            self.current_tail_page = new_page_id
            self.current_tail_offset = 0
        self.rid_counter += 1
        self.current_tail_offset += 1

    # Checks if page range is full based on page_id counter
    def _page_range_is_full(self, current_page, total_columns):
        return current_page > PAGE_RANGE_MAX_LEN - total_columns

    # Checks if page is full based on offset counter
    def _page_is_full(self, current_offset):
        return current_offset % (RECORDS_PER_PAGE - 1) == 0

    def __merge(self):
        print("merge is happening")
        pass
 
