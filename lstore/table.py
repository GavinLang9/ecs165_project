import os
from typing import Tuple
from lstore.index import Index
from lstore.bufferpool import BufferPool
from lstore.disk import Disk
from lstore.page import Page
import pdb
from time import time
from lstore.config import *
import struct

MERGE_FREQUENCY = RECORDS_PER_PAGE  # runs __merge() every x record updates

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
    def __init__(self, name, num_columns, key, path):
        self.path = path
        self.name = name
        self.key = key
        self.num_columns = num_columns
        self.page_directory = {}    # RID -> ([page_range_ids], [page_ids], [offsets])
        self.disk = Disk()
        self.bufferpool = BufferPool(BUFFER_POOL_CAPACITY, name, path)
        self.index = Index(self)    # Add this line for B-tree indexing
        self.rid_counter = 0
        self.num_tail_records = 0   # used to keep track of merge frequency
        
        # rest of your initialization code...

        # base page data
        self.current_base_page_range = 0
        self.current_base_page = 0   # page id of first column page
        self.current_base_offset = 0
        # tail page data
        self.current_tail_page_range = [0] * (num_columns + NUM_META_COLUMNS)
        self.current_tail_page = [0] * (num_columns + NUM_META_COLUMNS)
        self.current_tail_offset = [0] * (num_columns + NUM_META_COLUMNS)

        self.latest_page_range = 0
        self.latest_page = 0
        pass

    def serialize(self):
        serialized_data = b""

        # Serialize basic attributes
        serialized_data += struct.pack("I", len(self.name))  # Name length
        serialized_data += self.name.encode("utf-8")  # Table name
        serialized_data += struct.pack("I", self.num_columns)  # Number of columns
        serialized_data += struct.pack("I", self.key)  # Key index
        serialized_data += struct.pack("I", self.rid_counter)  # RID counter

        # Serialize page directory (RID -> [page_range_ids], [page_ids], [offsets])
        serialized_data += struct.pack("I", len(self.page_directory))  # Number of entries in the directory
        for rid, (page_range_ids, page_ids, offsets) in self.page_directory.items():
            page_range_ids = [page_range_id if page_range_id is not None else 4294967295 for page_range_id in page_range_ids]
            page_ids = [page_id if page_id is not None else 4294967295 for page_id in page_ids]
            offsets = [offset if offset is not None else 4294967295 for offset in offsets]
    

            # Serialize the data
            serialized_data += struct.pack("I", rid)  # RID
            serialized_data += struct.pack("I", len(page_range_ids))  # Number of page_range_ids
            serialized_data += b"".join(struct.pack("I", page_range_id) for page_range_id in page_range_ids)
            serialized_data += struct.pack("I", len(page_ids))  # Number of page_ids
            serialized_data += b"".join(struct.pack("I", page_id) for page_id in page_ids)
            serialized_data += struct.pack("I", len(offsets))  # Number of offsets
            serialized_data += b"".join(struct.pack("I", offset) for offset in offsets)

        # Serialize base page data
        serialized_data += struct.pack("I", self.current_base_page_range)
        serialized_data += struct.pack("I", self.current_base_page)
        serialized_data += struct.pack("I", self.current_base_offset)

        # Serialize tail page data
        serialized_data += b"".join(struct.pack("I", item) for item in self.current_tail_page_range)
        serialized_data += b"".join(struct.pack("I", item) for item in self.current_tail_page)
        serialized_data += b"".join(struct.pack("I", item) for item in self.current_tail_offset)

        # Serialize latest page data
        serialized_data += struct.pack("I", self.latest_page_range)
        serialized_data += struct.pack("I", self.latest_page)

        serialized_data += self.index.serialize()  

        return serialized_data
    

    @staticmethod
    def deserialize(serialized_data, path):
        """
        Deserialize binary data into a Table object.
        """
        index = 0
        name_len = struct.unpack("I", serialized_data[index:index + 4])[0]
        index += 4
        name = serialized_data[index:index + name_len].decode("utf-8")
        index += name_len
        num_columns = struct.unpack("I", serialized_data[index:index + 4])[0]
        index += 4
        key = struct.unpack("I", serialized_data[index:index + 4])[0]
        index += 4
        rid_counter = struct.unpack("I", serialized_data[index:index + 4])[0]
        index += 4

        page_directory_len = struct.unpack("I", serialized_data[index:index + 4])[0]
        index += 4
        page_directory = {}
        for _ in range(page_directory_len):
            rid = struct.unpack("I", serialized_data[index:index + 4])[0]

            index += 4
            page_range_ids_len = struct.unpack("I", serialized_data[index:index + 4])[0]

            index += 4
            page_range_ids = [struct.unpack("I", serialized_data[index + i:index + i + 4])[0] for i in range(0, page_range_ids_len * 4, 4)]
            page_range_ids = [page_range_id if page_range_id != 4294967295 else None for page_range_id in page_range_ids]

            index += page_range_ids_len * 4
            page_ids_len = struct.unpack("I", serialized_data[index:index + 4])[0]

            index += 4
            page_ids = [struct.unpack("I", serialized_data[index + i:index + i + 4])[0] for i in range(0, page_ids_len * 4, 4)]
            page_ids = [page_id if page_id != 4294967295 else None for page_id in page_ids]

            index += page_ids_len * 4
            offsets_len = struct.unpack("I", serialized_data[index:index + 4])[0]

            index += 4
            offsets = [struct.unpack("I", serialized_data[index + i:index + i + 4])[0] for i in range(0, offsets_len * 4, 4)]
            offsets = [offset if offset != 4294967295 else None for offset in offsets]

            index += offsets_len * 4
            page_directory[rid] = (page_range_ids, page_ids, offsets)

        current_base_page_range = struct.unpack("I", serialized_data[index:index + 4])[0]
        index += 4
        current_base_page = struct.unpack("I", serialized_data[index:index + 4])[0]
        index += 4
        current_base_offset = struct.unpack("I", serialized_data[index:index + 4])[0]
        index += 4

        current_tail_page_range = [struct.unpack("I", serialized_data[index + i:index + i + 4])[0] for i in range(0, (num_columns + NUM_META_COLUMNS) * 4, 4)]
        index += (num_columns + NUM_META_COLUMNS) * 4
        current_tail_page = [struct.unpack("I", serialized_data[index + i:index + i + 4])[0] for i in range(0, (num_columns + NUM_META_COLUMNS) * 4, 4)]
        index += (num_columns + NUM_META_COLUMNS) * 4
        current_tail_offset = [struct.unpack("I", serialized_data[index + i:index + i + 4])[0] for i in range(0, (num_columns + NUM_META_COLUMNS) * 4, 4)]
        index += (num_columns + NUM_META_COLUMNS) * 4

        latest_page_range = struct.unpack("I", serialized_data[index:index + 4])[0]
        index += 4
        latest_page = struct.unpack("I", serialized_data[index:index + 4])[0]
        index += 4


        # Deserialize the B-tree index
        index_data = serialized_data[index:]

        # Return a new Table object with the deserialized data
        table = Table(name, num_columns, key, path)
        table.page_directory = page_directory
        table.rid_counter = rid_counter
        table.current_base_page_range = current_base_page_range
        table.current_base_page = current_base_page
        table.current_base_offset = current_base_offset
        table.current_tail_page_range = current_tail_page_range
        table.current_tail_page = current_tail_page
        table.current_tail_offset = current_tail_offset
        table.latest_page_range = latest_page_range
        table.latest_page = latest_page
        index_obj = Index.deserialize(index_data, table)
        table.index = index_obj  # Assign the deserialized B-tree index

        return table

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
            int(0 * 1000),             # TIMESTAMP
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
            page.page_type = 'base'
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
        # if self.rid_counter == 3048:
        #     pdb.set_trace()
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
            int(0 * 1000),                     # TIMESTAMP
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
            page.page_type = 'tail'
            self.bufferpool.write_page(page_range_id, page_id, page)

            # update tail counters
            self.current_tail_page_range[i] = page_range_id
            self.current_tail_page[i] = page_id
        # Update table metadata
        # pdb.set_trace()
        self.page_directory[tail_rid] = (page_range_ids, column_page_ids, offsets)
        self._update_tail_indexes(offsets)
        self._update_base_record_metadata( base_rid, tail_rid, schema_encoding )
        self.num_tail_records += 1

        if self.num_tail_records % MERGE_FREQUENCY == 0:
            self.__merge()

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
        schema_encoding_int = int.from_bytes(self._convert_schema_encoding_to_bytes(schema_encoding), byteorder='big')
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

        # Update latest locations for pages to be placed
        if page_range_ids[-1] > self.latest_page_range:
            self.latest_page_range = page_range_ids[-1]
            self.latest_page = column_page_ids[-1]
        elif page_range_ids[-1] == self.latest_page_range:
            if column_page_ids[-1] > self.latest_page:
                self.latest_page = column_page_ids[-1]

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
                    next_free_page_range, next_free_page = self._next_free_location()
                    self.latest_page = next_free_page + 1 % PAGE_RANGE_MAX_LEN
                    if self.latest_page == 0:
                        self.latest_page_range += 1
                page_range_ids[i] = next_free_page_range
                column_page_ids[i] = next_free_page

        # for i in range(len(columns)):
        #     next_free_page = self.current_tail_page[i]
        #     next_free_page_range = self.current_tail_page_range[i]
        #     if columns[i] != None:
        #         if self.current_tail_offset[i] == 0:
        #             next_free_page = (self._next_free_page() + offset) % PAGE_RANGE_MAX_LEN
        #             offset += 1
        #         if next_free_page == 0 or next_free_page_range == 0:
        #             next_free_page_range = self._next_free_page_range()
        #             self.current_tail_page_range[i:] = [next_free_page_range] * (len(columns) - i)
        #         page_range_ids[i] = next_free_page_range
        #         column_page_ids[i] = next_free_page
            
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
            self.current_base_page_range, self.current_base_page = self._next_free_location()

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
                    self.current_tail_offset[i] = -1
                    self.current_tail_page_range[i], self.current_tail_page[i] = self._next_free_location()  # TODO: CONTINUE FIXING TAIL INDEX UPDATES
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
    
    def _next_free_location(self) -> Tuple[int, int]:
        """
        returns next empty page range and page id location
        """
        max_page_range = self.current_base_page_range
        max_page = (self.current_base_page + self.num_columns + NUM_META_COLUMNS) % PAGE_RANGE_MAX_LEN

        # if this page overflows into next page range
        if max_page < self.current_base_page:
            max_page_range += 1


        for i,(page_range, page) in enumerate(zip(self.current_tail_page_range, self.current_tail_page)):
            if page_range == max_page_range:
                if page > max_page:
                    max_page = page
                    continue
            elif page_range > max_page_range:
                max_page_range = page_range
                max_page = page
        if max_page >= PAGE_RANGE_MAX_LEN:
            max_page_range += 1
            max_page = 0
        return (max_page_range, max_page)

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
        return int(bit_string, 2).to_bytes(8, byteorder='big')
    
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
    
    def _missing_updated_columns(self, schema_encoding: list[int], columns) -> int:
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

    def _print_disk(self):
        disk_path = os.path.join(self.path, DISK_DIRECTORY_PATH, f'{self.name}.bin')
        num_bytes = os.path.getsize(disk_path)

        page_range_id = 0
        page_id = 0

        current_offset = page_range_id * PAGE_RANGE_MAX_LEN * (PAGE_SIZE +16) + (page_id * (PAGE_SIZE + 16))
        with open(disk_path, 'rb') as disk:
            bytes = disk.read(num_bytes)
            while current_offset < num_bytes:
                page = Page()
                page.num_records = int.from_bytes(bytes[current_offset: current_offset + 8], byteorder='big')
                page.data = bytes[current_offset + 16 : current_offset + PAGE_SIZE + 16]
                # print(f'page type: {page.page_type}\n')
                
                page_id += 1 % PAGE_RANGE_MAX_LEN
                if page_id == 0:
                    page_range_id += 1
                current_offset = page_range_id * PAGE_RANGE_MAX_LEN * (PAGE_SIZE +16) +(page_id * (PAGE_SIZE + 16))

    def print_page( self, page_range_id, page_id, num_records_to_print=RECORDS_PER_PAGE ):
        """
        Used for debugging: prints desired number of records of page to console
        """

        page = self.bufferpool.get_page( page_range_id, page_id )

        if not page:
            print("Invalid page")

        # exit if empty page
        if page.num_records == 0:
            print( "No records, empty page" )
            return

        # input validation
        if num_records_to_print > page.num_records:
            num_records_to_print = page.num_records

        # print out page data
        print( "Page being printed..." )
        print( "Page Range ID: ", page_range_id )
        print( "Page ID:       ", page_id )
        print( num_records_to_print, " of ", page.num_records, " printed." )

        for offset in range( num_records_to_print ):
            value = page[ offset ]
            print( offset, " | ", value )

    def _next_empty_locations( self ) -> Tuple[ list[int], list[int] ]:
        """
        Returns the next empty page locations
        """

        page_range_IDs = []
        page_IDs = []

        page_range_ID, page_ID = self._next_free_location()

        # search for empty pages until enough (total amount of columns) are found
        while len( page_range_IDs ) < ( NUM_META_COLUMNS + self.num_columns ):
            page = self.bufferpool.get_page( page_range_ID, page_ID )

            if not page:
                page_ID += 1
                if page_ID > PAGE_RANGE_MAX_LEN:
                    page_ID = 0
                    page_range_ID += 1
                continue

            if page.is_empty():
                page_range_IDs.append( page_range_ID )
                page_IDs.append( page_ID )

            # increment to next page
            page_ID += 1

            if page_ID > PAGE_RANGE_MAX_LEN:
                page_ID = 0
                page_range_ID += 1

        return ( page_range_IDs, page_IDs )

    def _get_condensed_base_write_locations( self ) -> Tuple[ list[int], list[int] ]:
        """
        Determines the page range and page index for each page of condensed base records to be written

        Returns:
            tuple: two lists
                - List of page_range_ids for each page/column
                - List of page_ids for each page/column

        Notes:
            Leaving current_base_page alone (might have empty space) and writing new condensed base pages at next
            available location
        """
        # default: write to self.current_base_page_range
        total_columns = self.num_columns + NUM_META_COLUMNS
        page_range_ids = [ self.current_base_page_range ] * total_columns
        page_ids = list( range( self._next_free_page(), self._next_free_page() + total_columns ) )

        # if no overflow, all columns go to current page range
        if not self._new_pages_will_overflow_page_range( self._next_free_page(), total_columns ):
            # account for next available page being in the next available page range
            if page_ids[0] == 0:
                page_range_ids = [ self._next_free_page_range() ] * total_columns

            return ( page_range_ids, page_ids )

        # Else, split columns into remaining space and next page range
        remaining_space = PAGE_RANGE_MAX_LEN - self._next_free_page()
        overflow_columns = total_columns - remaining_space

        page_range_ids = (
                [ self.current_base_page_range ] * remaining_space +
                [ self._next_free_page_range() ] * overflow_columns
        )

        page_ids = (
                list( range( self._next_free_page(), PAGE_RANGE_MAX_LEN )) +
                list( range( overflow_columns ) )
        )

        return ( page_range_ids, page_ids )

    def __merge(self):
        """
        Merges most recent tail records into their respective base records

        Order of Operations:
            Frequency: Once number of updates (tail records) reaches 50% (arbitrary value) of base records

            Load range of base pages into memory (outside of bufferpool)
            Iterate through tail records, updating base records in copied base pages
            Update page directory to point at new base pages (may need locking)


        Notes:
            Indirection column of updated base record is same as latest tail record
            No records are deleted/removed
            To change merge frequency, update MERGE_FREQUENCY variable
        """

        print("Merge is happening...")

        # NOTE: merge function currently occurs every 15 updates
        # TODO : get lock (?)
        # with self.lock:
        base_record_RIDs = self.index.locate_range(0, 906659770, self.key)
        base_record_RIDs = sorted( base_record_RIDs )  # TODO : double check how to correctly sort and interact with base_record_RIDs

        num_pages_per_col = int( (len( base_record_RIDs ) + RECORDS_PER_PAGE - 1) / RECORDS_PER_PAGE )
        num_remaining_base_records = len( base_record_RIDs )
        offsets = [ [] for _ in range(self.num_columns + NUM_META_COLUMNS) ]

        consolidated_base_pages = []

        # make new pages, populate with condensed base records
        for page_idx in range( num_pages_per_col ):
            consolidated_base_page_set = [ Page() for _ in range(self.num_columns + NUM_META_COLUMNS) ]

            # populate pages with condensed base records
            for base_record_idx in range( num_remaining_base_records ):
                # get latest record
                base_rid = base_record_RIDs[ (page_idx * RECORDS_PER_PAGE) + base_record_idx ][ 0 ]

                # testing
                base_record = self.get_record( base_rid )
                latest_record = self.get_latest_record( base_rid )
                metadata = [
                    base_rid,                       # Indirection
                    base_rid,                       # RID
                    int(time() * 1000),             # Timestamp
                    base_record.schema_encoding     # Schema Encoding
                ]
                consolidated_record_data = metadata + latest_record.columns

                # write values to corresponding pages
                for i, value in enumerate(consolidated_record_data):
                    index = consolidated_base_page_set[i].write( value )
                    offsets[i].append( index )
                    if base_record_idx >= RECORDS_PER_PAGE:
                        break

            num_remaining_base_records -= min( RECORDS_PER_PAGE, num_remaining_base_records )

            consolidated_base_pages.append( consolidated_base_page_set )

        # Write to disk
        for i, page_set in enumerate( consolidated_base_pages ):
            page_range_ids, page_ids = self._next_empty_locations()


            # write populated pages to disk
            for j, page in enumerate( page_set ):
                # self.print_page( page_range_ids[j], page_ids[j], 10)
                self.bufferpool.write_page( page_range_ids[j], page_ids[j], page )

            # update page directory
            num_base_records_in_page_set = min( len( base_record_RIDs ), len( base_record_RIDs ) - (RECORDS_PER_PAGE * i) )

            for j in range( num_base_records_in_page_set ):
                current_base_record_RID = base_record_RIDs[ (RECORDS_PER_PAGE*i) + j ][0]
                self.page_directory[ current_base_record_RID ] = ( page_range_ids, page_ids, [j] * len(page_ids) )

                if j >= RECORDS_PER_PAGE:
                    break


            # Write to disk
            # for page_set in consolidated_base_pages:
            #     for i, (page, base_rid) in enumerate(zip(page_set, base_record_RIDs)):
            #         page_range_ids, page_ids = self._get_base_write_locations()
            #
            #         self.bufferpool.write_page(page_range_ids[i], page_ids[i], page)
            #
            #         # Remap page directory
            #         # Extract the ith element from each sublist
            #         ith_elements = [sublist[i] for sublist in offsets if len(sublist) > i]
            #         self.page_directory[ base_rid[0] ] = (page_range_ids, page_ids, ith_elements)

            # TODO : Get bufferpool lock (?)
            # TODO: TPS

    # Might not be necessary - just delete rid from Index

    # def delete_record(self, base_rid: int):
    #     """
    #     Deletes a record by removing it from the page directory and updating relevant metadata.
    #     If the record is a base record, its tail records will also be handled.

    #     Args:
    #         base_rid (int): The rid of the record to be deleted.
    #     """
    #     base_record = self.get_record(base_rid)

    #     # Ensure the record exists and isn't already deleted
    #     if base_record is None:
    #         raise ValueError(f"Record with RID {base_rid} does not exist.")
        
    #     # Handle deletion of tail records if there are any
    #     current_tail_record = base_record
    #     while current_tail_record.indirection != current_tail_record.rid:
    #         # Get the next tail record
    #         next_tail_record = self.get_record(current_tail_record.indirection)
            
    #         # Mark this tail record for deletion
    #         self._delete_tail_record(next_tail_record.rid)
            
    #         current_tail_record = next_tail_record

    #     # Now, delete the base record
    #     self._delete_base_record(base_rid)

    #     # Optionally, update any metadata or internal structures to reflect the deleted record
    #     self.page_directory.pop(base_rid, None)


    # def _delete_tail_record(self, tail_rid: int):
    #     """
    #     Handles the deletion of a tail record by removing its pages from the buffer pool
    #     and updating the relevant page directory entries.
        
    #     Args:
    #         tail_rid (int): The rid of the tail record to delete.
    #     """
    #     page_range_ids, page_ids, offsets = self.page_directory.get(tail_rid, ([], [], []))

    #     # Loop through all pages related to this tail record and free them
    #     for page_range_id, page_id, offset in zip(page_range_ids, page_ids, offsets):
    #         page = self.bufferpool.get_page(page_range_id, page_id)
    #         if page:
    #             page.mark_as_deleted()  # You might need a method like this to mark pages as free
    #             self.bufferpool.write_page(page_range_id, page_id, page)

    #     # Remove the entry from the page directory
    #     self.page_directory.pop(tail_rid, None)

    # def _delete_base_record(self, base_rid: int):
    #     """
    #     Handles the deletion of a base record by updating the record's indirection and schema encoding.
    #     Removes the record from the page directory.

    #     Args:
    #         base_rid (int): The rid of the base record to delete.
    #     """
    #     base_record = self.get_record(base_rid)

    #     # Mark the base record as deleted (or set its indirection to itself if you want to preserve its space)
    #     self._write_record_column(base_rid, 0, base_rid)  # Set indirection to itself to signify deletion
    #     self._write_record_column(base_rid, 3, 0)  # Clear schema encoding (or set to a 'deleted' value)

    #     # Remove the entry from the page directory
    #     self.page_directory.pop(base_rid, None)
    
