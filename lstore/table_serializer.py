
import os
from lstore.config import *
from lstore.table import Table


class TableSerializer:
  
    def deserialize_table_meta_data(path, file) -> Table:
        """
        Reads in table metadata from metadata bin file
        """
        name = file.read(32).decode('utf-8').strip('\x00')
        key = int.from_bytes(file.read(1), byteorder='big')
        num_columns = int.from_bytes(file.read(1), byteorder='big')
        rid_counter = int.from_bytes(file.read(8), byteorder='big')
        current_base_page_range = int.from_bytes(file.read(8), byteorder='big')
        current_base_page = int.from_bytes(file.read(8), byteorder='big')
        current_base_offset = int.from_bytes(file.read(8), byteorder='big')
        current_tail_page_range = []
        current_tail_page = []
        current_tail_offset = []
        for i in range(num_columns + NUM_META_COLUMNS):
            tail_page_range = int.from_bytes(file.read(8), byteorder='big')
            current_tail_page_range.append(tail_page_range)
        for i in range(num_columns + NUM_META_COLUMNS):
            tail_page = int.from_bytes(file.read(8), byteorder='big')
            current_tail_page.append(tail_page)
        for i in range(num_columns + NUM_META_COLUMNS):
            tail_offset = int.from_bytes(file.read(8), byteorder='big')
            current_tail_offset.append(tail_offset)

        table = Table(name, num_columns, key)
        table.rid_counter = rid_counter
        table.current_base_page_range = current_base_page_range
        table.current_base_page = current_base_page
        table.current_base_offset = current_base_offset
        table.current_tail_page_range = current_tail_page_range
        table.current_tail_page = current_tail_page
        table.current_tail_offset = current_tail_offset
        table.path = path
        table.bufferpool.path = os.path.join(path, 'disk')

        return table

    
    def serialize_meta_data(table: Table) -> bytearray:
        """
        converts all metadata in table to a byte array:
            name - 32 B
            key - 1 B
            num_columns - 1 B
            page_directory - Will be converted in another function
            rid_counter = 8 B
            current_base_page_range = 8 B
            current_base_page = 8 B
            current_base_offset = 8 B
            current_tail_page_range = 8 B * num_columns
            current_tail_page = 8 B * num_columns
            current_tail_offset = 8 B * num_columns
        """
        data = bytearray(32)
        name_bytes = table.name.encode('utf-8')
        data[:len(name_bytes)] = name_bytes
        data.extend(table.key.to_bytes(1, byteorder='big'))
        data.extend(table.num_columns.to_bytes(1, byteorder='big'))
        data.extend(table.rid_counter.to_bytes(8, byteorder='big'))
        data.extend(table.current_base_page_range.to_bytes(8, byteorder='big'))
        data.extend(table.current_base_page.to_bytes(8, byteorder='big'))
        data.extend(table.current_base_offset.to_bytes(8, byteorder='big'))
        for i in range(table.num_columns + NUM_META_COLUMNS):
            data.extend(table.current_tail_page_range[i].to_bytes(8, byteorder='big'))
        for i in range(table.num_columns + NUM_META_COLUMNS):
            data.extend(table.current_tail_page[i].to_bytes(8, byteorder='big'))
        for i in range(table.num_columns + NUM_META_COLUMNS):
            data.extend(table.current_tail_offset[i].to_bytes(8, byteorder='big'))
        
        # print(data)
        return data
