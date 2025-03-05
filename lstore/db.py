import pdb
import pickle
from lstore.table import Table
from lstore.config import *
import os
class Database():

    def __init__(self):
        self.tables = []
        pass

    def open(self, path):
        self.path = path
        
        # Create directory if it doesn't exist
        if not os.path.exists(path):
            os.makedirs(path)
            disk_dir = os.path.join(self.path, DISK_DIRECTORY_PATH)
            # Create directory if it doesn't exist
            if not os.path.exists(disk_dir):
                    os.makedirs(disk_dir)
            return
        
        db_file = os.path.join(self.path, 'tables.pkl')
        
        if os.path.isfile(db_file):
            with open(db_file, 'rb') as file:
                self.tables = pickle.load(file)
                file.close()

    def close(self):
        """
        Serializes and writes all tables to disk using pickle.
        """
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        for table in self.tables:
            # Make sure to push all bufferpool pages to disk
            table.bufferpool.flush()

        db_file = os.path.join(self.path, "tables.pkl")
        
        with open(db_file, 'wb') as file:
            pickle.dump(self.tables, file)
            file.close()
            os.chmod(db_file, 0o777)
    """
    # Creates a new table
    :param name: string         #Table name
    :param num_columns: int     #Number of Columns: all columns are integer
    :param key: int             #Index of table key in columns
    """
    def create_table(self, name, num_columns, key_index):
        table = Table(name, num_columns, key_index, self.path)
        # table.path = self.path
        # table.bufferpool.path = os.path.join(self.path, DISK_DIRECTORY_PATH)
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
