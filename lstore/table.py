from lstore.index import Index
from lstore.page_range import PageRange
from lstore.page import Page
from time import time

INDIRECTION_COLUMN = 0
RID_COLUMN = 1
TIMESTAMP_COLUMN = 2
SCHEMA_ENCODING_COLUMN = 3

PAGE_RANGE_SIZE = 32

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
        self.total_columns = num_columns + 4
        self.page_directory = {} # RID -> (page_range, page_index, slot)
        self.index = Index(self)
        
    def __merge(self):
        print("merge is happening")
        pass
 
