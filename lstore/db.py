import pdb
from lstore.table import Table
from lstore.config import *
import os
import struct

class Database():

    def __init__(self):
        self.tables: list[Table] = []
        self.path = ""
        self.opened = False
        pass

    def open(self, path):
        self.path = path
        self.opened = True

        if not os.path.exists(path):
            os.makedirs(path)
            disk_dir = os.path.join(self.path, DISK_DIRECTORY_PATH)
            if not os.path.exists(disk_dir):
                    os.makedirs(disk_dir)
            return
        
        db_file = os.path.join(self.path + "/" + DISK_DIRECTORY_PATH, 'tables.bin')
        
        if os.path.isfile(db_file):
            with open(db_file, 'rb') as file:
                num_tables_data = file.read(4)
                if len(num_tables_data) < 4:
                    raise ValueError("File too small: missing number of tables")

                num_tables = struct.unpack("I", num_tables_data)[0]

                self.tables = []
                for _ in range(num_tables):
                    table_data = file.read()  # Assuming the remaining data corresponds to one table
                    if not table_data:
                        raise ValueError("No more data for table")
                    table = Table.deserialize(table_data, self.path)
                    self.tables.append(table)

    def close(self):
        """
        Serializes and writes all tables to disk using pickle.
        """
        # write pages to disk
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        for table in self.tables:
            table.bufferpool.flush()

        db_file = os.path.join(self.path + "/" + DISK_DIRECTORY_PATH, "tables.bin")
        
        # write tables to disk
        with open(db_file, 'wb') as file:
            # Write number of tables
            file.write(struct.pack("I", len(self.tables)))

            for table in self.tables:
                # Serialize the table and write the serialized data to the file
                serialized_table_data = table.serialize()
                file.write(serialized_table_data)
                

    """
    # Creates a new table
    :param name: string         #Table name
    :param num_columns: int     #Number of Columns: all columns are integer
    :param key: int             #Index of table key in columns
    """
    def create_table(self, name, num_columns, key_index):
        if not self.opened:
            default_path = "./default_path"  # Choose a reasonable default
            self.open(default_path)  # Open with a default path if not explicitly opened


        table = Table(name, num_columns, key_index, self.path)
        # table.path = self.path
        # table.bufferpool.path = os.path.join(self.path, DISK_DIRECTORY_PATH)
        self.tables.append(table)
        
        return table

    
    """
    # Deletes the specified table
    """
    def drop_table(self, name):
        for table in self.tables:
            if table.name == name:
                self.tables.remove(table)
                return

    
    """
    # Returns table with the passed name
    """
    def get_table(self, name):
        for table in self.tables:
            if table.name == name:
                return table
        return False
