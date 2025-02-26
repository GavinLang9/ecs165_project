from lstore.table import Table
import pickle
import os

class Database():

    def __init__(self):
        self.tables = []
        self.path = None
        pass

    def open(self, path):
        self.path = path

        if not os.path.exists(path):
            with open(path, "wb") as f:
                pickle.dump([], f) 

        with open(path, "rb") as f:
            try:
                self.tables = pickle.load(f)
                if not isinstance(self.tables, list):
                    self.tables = []
            except (EOFError, pickle.UnpicklingError):
                self.tables = []

                

    def close(self):
        with open(self.path, "wb") as f:
            pickle.dump(self.tables, f)
            f.close()
    """
    # Creates a new table
    :param name: string         #Table name
    :param num_columns: int     #Number of Columns: all columns are integer
    :param key: int             #Index of table key in columns
    """
    def create_table(self, name, num_columns, key_index):
        table = Table(name, num_columns, key_index)
        self.tables.append(table)
        return table

    
    """
    # Deletes the specified table
    """
    def drop_table(self, name):
        table_to_remove = next((table for table in self.tables if table.name == name), None)
        self.tables.remove(table_to_remove)

    
    """
    # Returns table with the passed name
    """
    def get_table(self, name):
        return next((table for table in self.tables if table.name == name), None)
