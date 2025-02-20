import json
import pdb
import struct
from lstore.btree import Btree, Node
from lstore.index import Index
from lstore.table import Table
import os
from lstore.config import *
from lstore.index_serializer import IndexSerializer
from lstore.page_directory_serializer import PageDirectorySerializer
from lstore.table_serializer import TableSerializer
class Database():

    def __init__(self):
        self.tables = []
        self.path = ''
        pass

    # Not required for milestone1
    def open(self, path):
        """
        constructs tables from disk data or just creates disk directories if disk
        doesn't exist
        """
        self.path = path
        
        # Create directories for storing bin and json data
        if not os.path.exists(path):
            os.makedirs(path)
            dirs = (os.path.join(self.path ,META_DATA_PATH), \
                os.path.join(self.path, PAGE_DIRECTORY_PATH), \
                os.path.join(self.path, INDEX_DIRECTORY_PATH), \
                os.path.join(self.path, DISK_DIRECTORY_PATH)    )
            # Create directory if it doesn't exist
            for dir in dirs:
                if not os.path.exists(dir):
                    os.makedirs(dir)
            return
        
        meta_data_dir = path + '/' + META_DATA_PATH
        page_directory_dir = path + '/' + PAGE_DIRECTORY_PATH
        index_dir = path + '/' + INDEX_DIRECTORY_PATH

        for filename in os.listdir(meta_data_dir):
            # Get paths to files for data
            meta_data_path = os.path.join(meta_data_dir, filename)
            page_directory_path = os.path.join(page_directory_dir, filename)
            # index is stored as json since it is a complex data structure
            index_path = os.path.join(index_dir, f'{os.path.splitext(filename)[0]}.json')

            # deserializes data from disk files and constructs tables
            if os.path.isfile(meta_data_path):
                with open(meta_data_path, 'rb') as file:
                    table = TableSerializer.deserialize_table_meta_data(path, file)
                with open(page_directory_path, 'rb') as file:
                    table.page_directory = PageDirectorySerializer.deserialize_page_directory(file, table.num_columns)
                with open(index_path, 'r') as file:
                    data = json.load(file)
                    table.index = IndexSerializer.deserialize_index(data, table)
                self.tables.append(table)

    def close(self):
        """
        Writes every table to disk
            - Creates 4 directories.  1 to store metadata, 1 to store the page dir, 
            1 to store index data, and 1 to store the actual table data
        """
        dirs = (os.path.join(self.path ,META_DATA_PATH), \
                os.path.join(self.path, PAGE_DIRECTORY_PATH), \
                os.path.join(self.path, INDEX_DIRECTORY_PATH), \
                os.path.join(self.path, DISK_DIRECTORY_PATH)    )
        # Create directory if it doesn't exist
        for dir in dirs:
            if not os.path.exists(dir):
                os.makedirs(dir)
        
        for table in self.tables:
            # Make sure to push all bufferpool pages to disk
            table.bufferpool.flush()
            name = table.name

            # Get paths to files to write data to as well as serialized data
            meta_data_path = os.path.join(self.path ,META_DATA_PATH, f'{name}.bin')
            meta_data_bytes = TableSerializer.serialize_meta_data(table)

            page_directory_path = os.path.join(self.path, PAGE_DIRECTORY_PATH, f'{name}.bin')
            page_directory_bytes = PageDirectorySerializer.serialize_page_directory(table)
            
            index_path = os.path.join(self.path, INDEX_DIRECTORY_PATH, f'{name}.json')
            index_json = IndexSerializer.serialize_index(table.index)

            with open(meta_data_path, 'wb') as file:
                file.write(meta_data_bytes)
                os.chmod(meta_data_path, 0o777)

            with open(page_directory_path, 'wb') as file:
                file.write(page_directory_bytes)
                os.chmod(page_directory_path, 0o777)

            with open(index_path, 'w') as file:
                json.dump(index_json, file, indent=2)
                os.chmod(index_path, 0o777)

    """
    # Creates a new table
    :param name: string         #Table name
    :param num_columns: int     #Number of Columns: all columns are integer
    :param key: int             #Index of table key in columns
    """
    def create_table(self, name, num_columns, key_index):
        table = Table(name, num_columns, key_index)
        table.path = self.path
        table.bufferpool.path = os.path.join(self.path, DISK_DIRECTORY_PATH)
        self.tables.append(table)
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


  
    
