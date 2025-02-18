import pdb
from lstore.index import Index
from lstore.table import Table
import os
from lstore.config import *
class Database():

    def __init__(self):
        self.tables = []
        self.path = ''
        pass

    # Not required for milestone1
    def open(self, path):
        self.path = path
        if not os.path.exists(path):
            os.makedirs(path)
            return
        meta_data_dir = path + '/' + META_DATA_PATH
        page_directory_dir = path + '/' + PAGE_DIRECTORY_PATH
        for filename in os.listdir(meta_data_dir):
            meta_data_path = os.path.join(meta_data_dir, filename)
            page_directory_path = os.path.join(page_directory_dir, filename)
            if os.path.isfile(meta_data_path):
                with open(meta_data_path, 'rb') as file:
                    table = self._read_table_meta_data(file)
                with open(page_directory_path, 'rb') as file:
                    table.page_directory = self._read_page_directory(file, table.num_columns)
                self.tables.append(table)

    def close(self):
        """
        Writes every table to disk
            - Creates 3 directories.  1 to store metadata, 1 to store the page dir,
            and 1 to store the actual table data
        """
        

        dirs = (os.path.join(self.path ,META_DATA_PATH), os.path.join(self.path, PAGE_DIRECTORY_PATH))
        # Create directory if it doesn't exist
        for dir in dirs:
            if not os.path.exists(dir):
                os.makedirs(dir)
        
        for table in self.tables:
            name = table.name

            meta_data_path = os.path.join(self.path ,META_DATA_PATH, f'{name}.bin')
            meta_data_bytes = self._convert_meta_data_to_bytes(table)

            page_directory_path = os.path.join(self.path, PAGE_DIRECTORY_PATH, f'{name}.bin')
            page_directory_bytes = self._convert_page_directory_to_bytes(table)
            # data_directory_path = os.path.join(data_dir, f'{name}.bin')
            # data_directory_bytes = self._convert_data_to_bytes
            # index_directory_path = os.path.join(self.path, INDEX_DIRECTORY_PATH, f'{name}.bin')
            # index_bytes = self._convert_index_to_bytes(table.index)

            with open(meta_data_path, 'wb') as file:
                file.write(meta_data_bytes)
                os.chmod(meta_data_path, 0o777)

            with open(page_directory_path, 'wb') as file:
                file.write(page_directory_bytes)
                os.chmod(page_directory_path, 0o777)

    """
    # Creates a new table
    :param name: string         #Table name
    :param num_columns: int     #Number of Columns: all columns are integer
    :param key: int             #Index of table key in columns
    """
    def create_table(self, name, num_columns, key_index):
        table = Table(name, num_columns, key_index)
        self.tables.append(table)
        # print(self.tables[0])
        return table

    
    """
    # Deletes the specified table
    """
    def drop_table(self, name):
        pass

    
    """
    # Returns table with the passed name
    """
    def get_table(self, name):
        for table in self.tables:
            if table.name == name:
                return table
        return False

    def _read_table_meta_data(self, file) -> Table:
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
        table.path = self.path

        return table

    
    def _convert_meta_data_to_bytes(self, table: Table) -> bytearray:
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

    def _read_page_directory(self, file, num_columns) -> dict:
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

    def _convert_page_directory_to_bytes(self, table: Table) -> bytearray:
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
            for i in range(table.num_columns):
                data.extend(page_range_ids[i].to_bytes(8, byteorder='big'))
            for i in range(table.num_columns):
                data.extend(page_ids[i].to_bytes(8, byteorder='big'))
            for i in range(table.num_columns):
                data.extend(offsets[i].to_bytes(8, byteorder='big'))
        
        return data  
    
    def _convert_index_to_bytes(self, index: Index) -> bytearray:
        pass