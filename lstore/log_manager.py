from typing import List
from time import time

class LogEntry:
    def __init__(self, transaction_id, table_id, key, type, old_values=None, new_values=None, table=None):
        self.transaction_id = transaction_id
        self.table_id = table_id
        self.key = key
        self.type = type
        self.old_values = old_values
        self.new_values = new_values
        self.table = table
        self.timestamp = time()

class LogManager:
    def __init__(self):
        self.entries: List[LogEntry]  = []

    def add(self, transaction_id, table_id, key, type, old_values=None, new_values=None, table=None):
        self.entries.append(
            LogEntry(
                transaction_id=transaction_id,
                table_id=table_id,
                key=key,
                type=type,
                old_values=old_values,
                new_values=new_values,
                table=table,
            )
        )
            