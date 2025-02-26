from lstore.config import *
from lstore.table import Table

class PageDirectorySerializer:
    def deserialize_page_directory(file, num_columns) -> dict:
        page_directory = {}
        num_entries = int.from_bytes(file.read(8), byteorder='big')
        for key in range(num_entries):
            page_range_ids = []
            page_ids = []
            offsets = []
            for i in range(num_columns + NUM_META_COLUMNS):
                page_range_ids.append(int.from_bytes(file.read(8), byteorder='big'))
            for i in range(num_columns + NUM_META_COLUMNS):
                page_ids.append(int.from_bytes(file.read(8), byteorder='big'))
            for i in range(num_columns + NUM_META_COLUMNS):
                offsets.append(int.from_bytes(file.read(8), byteorder='big'))
            page_directory[key] = (page_range_ids, page_ids, offsets)
        return page_directory

    def serialize_page_directory(table: Table) -> bytearray:
        """
        converts page_directory to byte arrays
            first 8 bytes are length of page_directory
            for each rid:
                page_range_id - 8 B * num_columns
                page_id - 8 B * num_columns
                offset - 8 B * num_columns

        when reading from bytes back to hash table, each rid will correspond
        to 3 * num_columns * 8 bytes
        """
        data = bytearray()
        data[0:8] = len(table.page_directory).to_bytes(8, byteorder='big')

        for key in table.page_directory:
            page_range_ids, page_ids, offsets = table.page_directory[key]
            for i in range(table.num_columns + NUM_META_COLUMNS):
                data.extend(page_range_ids[i].to_bytes(8, byteorder='big'))
            for i in range(table.num_columns + NUM_META_COLUMNS):
                data.extend(page_ids[i].to_bytes(8, byteorder='big'))
            for i in range(table.num_columns + NUM_META_COLUMNS):
                data.extend(offsets[i].to_bytes(8, byteorder='big'))
        
        return data  