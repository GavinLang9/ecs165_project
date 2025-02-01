from typing import Tuple
from lstore.index import Index
from lstore.bufferpool import BufferPool
from time import time

INDIRECTION_COLUMN = 0
RID_COLUMN = 1
TIMESTAMP_COLUMN = 2
SCHEMA_ENCODING_COLUMN = 3

BUFFER_POOL_CAPACITY = 16
RECORDS_PER_PAGE = 512
PAGE_RANGE_MAX_LEN = 64

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
        self.page_directory = {}    # RID -> (page_range_id, page_id) ?
        self.bufferpool = BufferPool(BUFFER_POOL_CAPACITY)
        self.index = Index(self)
        self.rid_counter = 0
        self.current_page_range = 0
        self.current_page = 0   # page id of first column page

        pass

    def create_record(self, key, columns):
        """
        Creates a new record by writing columns to their corresponding pages.
        
        Args:
            key (int): Primary key value
            columns (list[int]): List of column values to write
            
        """
        # create meta data columns
        if len(columns != self.num_columns):
            raise ValueError("Invalid number of columns")
        rid = self.rid_counter
        metadata = [
            rid,                            # INDIRECTION
            rid,                            # RID
            int(time() * 1000),             # TIMESTAMP
            '0' * self.num_columns,          # SCHEMA ENCODING
            key
        ]
        record_data =  metadata + columns

        # returns a tuple of lists that hold page range and page indexes for each column
        page_range_ids, column_page_ids = self._get_write_locations()
        offsets = []
        # write each column to their correspoding location in disk
        for value, page_range_id, page_id in zip(record_data, page_range_ids, column_page_ids):
            page = self.bufferpool.get_page(page_range_id, page_id)
            if not page.has_capacity():
                raise IndexError("This page has no space")
            index = page.write(value)
            offsets.append(index)
            self.bufferpool.write(page_range_id, page_id, page)
        
        # TODO: Maybe call bufferpool.flush to commit
        # Update table metadata
        # TODO: Fix page directory to include offset in page and update this everywhere else
        self.page_directory[rid] = (page_range_ids, column_page_ids, offsets)
        self._update_indexes(rid)
        
    def get_record(self, rid: int, projected_columns_index: list[int]):
        page_range_ids, page_ids, offsets = self.page_directory[rid]
        columns = []
        for page_range_id, page_id, offset in zip(page_range_ids, page_ids, offsets):
            page = self.bufferpool.get_page(page_range_id, page_id)
            value = page[offset]
            columns.append(value)
        # TODO: Continue working on get_record 

    def _new_pages_will_overflow_page_range(self, total_columns):
        """
        Checks if writing new pages would exceed the current page range capacity.
        
        Args:
            total_columns (int): Number of columns to be written
            
        Returns:
            bool: True if writing would overflow the current page range
        """
        return self.current_page + total_columns > PAGE_RANGE_MAX_LEN         

    def _get_write_locations(self) -> Tuple[list, list]:
        """
        Determines the page range and page index for each column to be written.
        
        Returns:
            tuple: Contains two lists:
                - List of page_range_ids for each column
                - List of page_ids for each column
        """
        # Default all columns will be written to self.current_page_range
        total_columns = self.num_columns + 4
        page_range_ids = [self.current_page_range] * total_columns
        column_page_ids = [self.current_page] * total_columns
        
        # If no overflow, all columns go to current page range
        if not self._new_pages_will_overflow_page_range():
            return (page_range_ids, column_page_ids)

        # Else, split columns into remaining space and next page range
        remaining_space = PAGE_RANGE_MAX_LEN - self.current_page # number of columns that will be stored in current page
        overflow_columns = total_columns - remaining_space

        page_range_ids = (
            [self.current_page_range] * remaining_space +
            [self.current_page_range + 1] * overflow_columns
        )

        column_page_ids = (
            list(range(self.current_page, PAGE_RANGE_MAX_LEN)) + 
            list(range(overflow_columns))
        )
        
        return (page_range_ids, column_page_ids)

    def _update_indexes(self, rid: int):
        """
        Update table counters for  
            page range  
            page id  
            rid  
        """
        if rid % (RECORDS_PER_PAGE - 1) == 0:
            if self.current_page == PAGE_RANGE_MAX_LEN - 1:
                self.current_page_range += 1
                self.current_page = 0
            else:
                self.current_page += 1
        self.rid_counter += 1

    def __merge(self):
        print("merge is happening")
        pass
 
