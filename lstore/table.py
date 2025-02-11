from typing import Tuple
from lstore.index import Index
from lstore.bufferpool import BufferPool
from lstore.disk import Disk
from lstore.page import Page
import pdb
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
    def __init__(self, rid, indirection, schema_encoding, key, columns):
        self.rid = rid
        self.indirection = indirection
        self.schema_encoding = schema_encoding
        self.key = key
        self.columns = columns
    
    def __str__(self):
        s = ''
        s += f'rid: {self.rid}\n'
        s += f'indirection: {self.indirection}\n'
        s += f'schema encoding: {self.schema_encoding}\n'
        s += f'key: {self.key}\n'
        s += f'columns: {self.columns}\n'
        return s

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
        self.index = Index(self)    # Add this line for B-tree indexing
        self.rid_counter = 0
        
        # rest of your initialization code...

        # base page data
        self.current_base_page_range = 0
        self.current_base_page = 0   # page id of first column page
        self.current_base_offset = 0
        # tail page data
        self.current_tail_page_range = [0] * (num_columns + NUM_META_COLUMNS)
        self.current_tail_page = [0] * (num_columns + NUM_META_COLUMNS)
        self.current_tail_offset = [0] * (num_columns + NUM_META_COLUMNS)
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
            0            # SCHEMA ENCODING
        ]
        record_data = metadata + list(columns)

        # returns a tuple of lists that hold page range and page indexes for each column
        page_range_ids, column_page_ids = self._get_base_write_locations()

        offsets = []
        # write each column to their corresponding location in disk
        for i, (value, page_range_id, page_id) in enumerate(zip(record_data, page_range_ids, column_page_ids)):
            page = self.bufferpool.get_page(page_range_id, page_id)

            if not page:
                page = Page()
                
            if not page.has_capacity():
                page = Page()
                page_id = self._next_free_page()
                if page_id == 0:
                    page_range_id = self._next_free_page_range()
                page_range_ids[i] = page_range_id
                column_page_ids[i] = page_id
                # raise IndexError("This page has no space")

            index = page.write(value)
            offsets.append(index)
            self.bufferpool.write_page(page_range_id, page_id, page)
        # Update table metadata
        self.page_directory[rid] = (page_range_ids, column_page_ids, offsets)
        self._update_base_indexes()

    def update_record(self, base_rid, columns):
        """
        Updates a record by writing columns to their corresponding tail pages
        and updating the base record indirection and schema encoding.

        Args:
            base_rid (int): rid of record to be updated
            columns (tuple): List of column values to write
                first column is key column (usually)
                [key, col 1, None, col 3, ...]
        """
        # create meta data columns
        # pdb.set_trace()
        if len(columns) != self.num_columns:
            raise ValueError("Invalid number of columns")
        base_record = self.get_record(base_rid)
        indirection_rid = base_record.indirection
        tail_rid = self.rid_counter
        base_schema_encoding = self._convert_int_to_schema_encoding(base_record.schema_encoding)
        schema_encoding = self._get_schema_encoding( columns )
        schema_encoding = self._logical_or(base_schema_encoding, schema_encoding)
        schema_encoding_bytes = self._convert_schema_encoding_to_bytes(schema_encoding)

        metadata = [
            indirection_rid,                   # INDIRECTION (previous tail record's RID)
            tail_rid,                          # RID
            int(time() * 1000),                # TIMESTAMP
            schema_encoding_bytes              # SCHEMA ENCODING
        ]

        record_data = metadata + list( columns )

        # returns a tuple of lists that hold page range and page indexes for each column
        page_range_ids, column_page_ids = self._get_tail_write_locations(record_data)

        offsets = [None] * len(record_data)
        # write each column to their corresponding location in disk
        for i,(value, page_range_id, page_id) in enumerate(zip(record_data, page_range_ids, column_page_ids)):
            if value == None:
                continue
            page = self.bufferpool.get_page(page_range_id, page_id)

            if not page:
                page = Page()

            if not page.has_capacity():
                page = Page()
                page_id = self._next_free_page()
                if page_id == 0:
                    page_range_id = self._next_free_page_range()
                page_range_ids[i] = page_range_id
                column_page_ids[i] = page_id                
                # raise IndexError("This page has no space")

            index = page.write(value)
            offsets[i] = index
            self.bufferpool.write_page(page_range_id, page_id, page)

            # update tail counters
            self.current_tail_page_range[i] = page_range_id
            self.current_tail_page[i] = page_id
        # Update table metadata
        # pdb.set_trace()
        self.page_directory[tail_rid] = (page_range_ids, column_page_ids, offsets)
        self._update_tail_indexes(offsets)
        self._update_base_record_metadata( base_rid, tail_rid, schema_encoding )

    def get_latest_record(self, base_rid: int) -> Record:
        """
        Gets the most recent version of the record and
        returns constructed record by getting each column value from their respective pages
        :param rid: base record RID

        Note: base record indirection is latest tail record RID,
              tail record indirection is previous tail record RID
        """

        base_record = self.get_record( base_rid )
        schema_encoding = self._convert_int_to_schema_encoding(base_record.schema_encoding)

        # return record if indirection is RID
        # AKA return record if it is the base record (has no updates)
        if base_record.indirection == base_record.rid:
            return base_record
        
        current_tail_record = self.get_record( base_record.indirection )
        columns = current_tail_record.columns

        while self._missing_updated_columns(schema_encoding, columns):
            next_tail_record = self.get_record(current_tail_record.indirection)
            if next_tail_record.rid == current_tail_record.rid:
                raise ValueError('cannot fill all columns in schema encoding')
            for index, col in enumerate(next_tail_record.columns):
                if columns[index] == None and col != None:
                    columns[index] = col
            current_tail_record = next_tail_record

        latest_tail_record = Record(None, None, None, None, columns)
        # Using cumulative tail records
        # Fill in all None values with base record values
        latest_tail_record = self._get_cumulative_tail_record_columns(latest_tail_record, base_record)

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

    def _get_cumulative_tail_record_columns(self, latest_tail_record: Record, base_record: Record):
        """
        Returns the cumulative tail based off of previous tail record and new columns values

        :param latest_tail_record: Record object, most recent tail record
        :param columns: tuple of values
        """
        for i, column in enumerate(latest_tail_record.columns):
            if column is None:
                latest_tail_record.columns[i] = base_record.columns[i]
        if latest_tail_record.key is None:
            latest_tail_record.key = base_record.key
        
        return latest_tail_record
        

    def _update_base_record_metadata(self, base_rid: int, tail_rid: int, schema_encoding):
        """
        updates indirection and schema encoding columns for a base page

        """
        self._write_record_column(base_rid, 0, tail_rid)
        schema_encoding_int = int.from_bytes(self._convert_schema_encoding_to_bytes(schema_encoding))
        self._write_record_column(base_rid, 3, schema_encoding_int)

    def get_record(self, rid: int) -> Record:
        """
        returns constructed record by getting each column value from their respective pages
        """
        
        page_range_ids, page_ids, offsets = self.page_directory[rid]
        columns = []
        # if rid == 16196:
            # pdb.set_trace()
        for page_range_id, page_id, offset in zip(page_range_ids, page_ids, offsets):
            if page_range_id == None or page_id == None or offset == None:
                columns.append(None)
                continue
            # if page_range_id == 20695 and page_id == 58 and offset == 0:
            #     pdb.set_trace()
            page = self.bufferpool.get_page(page_range_id, page_id)
            if page is None:
                columns.append(None)
                continue
            value = page[offset]
            columns.append(value)
        
        record = Record(rid, columns[INDIRECTION_COLUMN], columns[SCHEMA_ENCODING_COLUMN], columns[self.key + NUM_META_COLUMNS], columns[4:]) # 4 columns of metadata followed by key
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

    def _get_tail_write_locations(self, columns: tuple) -> Tuple[list[int], list[int]]:
        """
        Determines the page range and page index for each column to be written.

        Returns:
            tuple: Contains two lists:
                - List of page_range_ids for each column
                - List of page_ids for each column
        """
        
        total_columns = self.num_columns + NUM_META_COLUMNS

        page_range_ids = [None] * total_columns
        column_page_ids = [None] * total_columns

        # Initialize updated columns so we don't allocate tail pages we don't need
        offset = 0

        # Goes through updated column and either gets the location of a page that is not full
        # or allocates a new page for that column
        # Sorry for how ugly this is, it was a bit hard to implement
        for i in range(len(columns)):
            next_free_page = self.current_tail_page[i]
            next_free_page_range = self.current_tail_page_range[i]
            if columns[i] != None:
                if self.current_tail_offset[i] == 0:
                    next_free_page = (self._next_free_page() + offset) % PAGE_RANGE_MAX_LEN
                    offset += 1
                if next_free_page == 0 or next_free_page_range == 0:
                    next_free_page_range = self._next_free_page_range()
                    self.current_tail_page_range[i:] = [next_free_page_range] * (len(columns) - i)
                page_range_ids[i] = next_free_page_range
                column_page_ids[i] = next_free_page

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
                self.current_base_page_range = self._next_free_page_range()
            new_page_id = (self.current_base_page + total_columns) % PAGE_RANGE_MAX_LEN
            self.current_base_page = new_page_id
            self.current_base_offset = 0
        self.rid_counter += 1
        self.current_base_offset += 1

    def _update_tail_indexes(self, offsets):
        """
        Update table counters for
            page range
            page id
            offset
            rid
        """
        total_columns = self.num_columns + NUM_META_COLUMNS

        for i, offset in enumerate(offsets):
            if offset != None:
                if offset >= RECORDS_PER_PAGE - 1:
                    self.current_tail_offset[i] = 0
                    self.current_tail_page[i] = self._next_free_page()
                    if self.current_tail_page == 0:
                        self.current_tail_page_range[i] = self._next_free_page_range()
                self.current_tail_offset[i] += 1
        self.rid_counter += 1

    def _next_free_page(self):
        """
        returns next empty page index
        """
        total_columns = NUM_META_COLUMNS + self.num_columns
        next_page_id = max(self.current_base_page + total_columns, max(self.current_tail_page) + 1)
        if next_page_id >= PAGE_RANGE_MAX_LEN:
            return 0
        return next_page_id

    def _next_free_page_range(self):
        """
        returns next empty page range index
        """
        next_page_range = max(self.current_base_page_range + 1, max(self.current_tail_page_range) + 1)
        return next_page_range
    
    def _write_record_column(self, rid, column_index, value):
        """
        updates single page for a column (for indirection and schema encoding)
        
        Args:
            rid: rid of record to be updated
            column_index: index of column to be updated
            value: (rid or schema encoding) to be writen to page
        """
        page_range_ids, page_ids, offsets = self.page_directory[rid]
        page_range_id = page_range_ids[column_index]
        page_id = page_ids[column_index]
        offset = offsets[column_index]
        page = self.bufferpool.get_page(page_range_id, page_id)

        page.update(offset, value)

        self.bufferpool.write_page(page_range_id, page_id, page)
    
    def _convert_schema_encoding_to_bytes(self, schema_encoding: list[int]) -> bytearray:
        bit_string = ''.join(map(str, schema_encoding))
        return int(bit_string, 2).to_bytes(8)
    
    def _convert_int_to_schema_encoding(self, schema_encoding: int) -> list[int]:
        bit_string = bin(schema_encoding)[2:].zfill(self.num_columns)
    
        # Return a list of bits as integers
        return [int(bit) for bit in bit_string]
    
    def _logical_or(self, arr1, arr2):
        """
        Performs a logical OR operation on two arrays of 0s and 1s.

        Args:
            arr1: The first array.
            arr2: The second array.

        Returns:
            A new array with the result of the logical OR operation.
        """

        if len(arr1) != len(arr2):
            raise ValueError("Arrays must have the same length")

        result = []
        for i in range(len(arr1)):
            result.append(1 if (arr1[i] or arr2[i]) else 0)
        return result
    
    def _missing_updated_columns(self, schema_encoding: list[int], columns: list[int | None]) -> int:
    # Ensure both arrays have the same length
        if len(schema_encoding) != len(columns):
            pdb.set_trace()
            raise ValueError("Arrays must have the same length.")

        # Count mismatches where schema_encoding is 1, but the columns array has None
        return sum(1 for b, m in zip(schema_encoding, columns) if b == 1 and m is None)
    
    # Checks if page range is full based on page_id counter
    def _page_range_is_full(self, current_page, total_columns):
        return current_page > PAGE_RANGE_MAX_LEN - total_columns

    # Checks if page is full based on offset counter
    def _page_is_full(self, current_offset):
        return current_offset % (RECORDS_PER_PAGE - 1) == 0

    def __merge(self):
        print("merge is happening")
        pass
 
