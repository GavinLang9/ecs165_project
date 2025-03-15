from lstore.table import Table, Record
from lstore.index import Index
from lstore.lock_manager import LockManager, LockType
from lstore.log_manager import LogManager
from enum import Enum

class TransactionType(Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    SELECT = "select"
    SELECT_VERSION = "select_version"
    SUM = "sum"
    SUM_VERSION = "sum_version"


class Transaction:
    """
    # Creates a transaction object.
    Implements the Two-Phase Locking protocol with Write-Ahead Logging.
    """

    _lock_manager = None
    _log_manager = None
    
    @classmethod
    def lock_manager_instance(cls) -> LockManager:
        """
        returns shared lock manager instance
        """
        if cls._lock_manager is None:
            cls._lock_manager = LockManager()
        return cls._lock_manager
    
    @classmethod
    def log_manager_instance(cls) -> LogManager:
        if cls._log_manager is None:
            cls._log_manager = LogManager()
        return cls._log_manager
    
    def __init__(self):
        self.queries = []  
        self.transaction_id = id(self)
    
    def add_query(self, query, table, *args):
        """
        # Adds the given query to this transaction
        """
        self.queries.append((query, table, args))
    
    def run(self):
        """
        Runs the transaction with Two-Phase Locking protocol
        """
        try:
            if not self._acquire_all_locks():
                return self.abort()
            for query, table, args in self.queries:
                query_name = getattr(query, '__name__', str(query))
                if query_name == TransactionType.UPDATE.value:
                    old_values = table.transaction_get_record(args[0])
                    new_values = [a if b is None else b for a, b in zip(old_values[1:], args[2:])]

                    self.log_manager_instance().add(
                        transaction_id=self.transaction_id,
                        table_id=id(table),
                        key=args[0],
                        type=TransactionType.UPDATE.value,
                        old_values=old_values[1:],
                        new_values=new_values,
                        table=table,
                    )
                elif query_name == TransactionType.INSERT.value:
                    self.log_manager_instance().add(
                        transaction_id=self.transaction_id,
                        table_id=id(table),
                        key=args[0],
                        type=TransactionType.INSERT.value,
                        old_values=None,
                        new_values=args[1:],
                        table=table,
                    )
                elif query_name == TransactionType.DELETE.value:
                    old_values = table.transaction_get_record(args[0])
                    self.log_manager_instance().add(
                        transaction_id=self.transaction_id,
                        table_id=id(table),
                        key=args[0],
                        type=TransactionType.DELETE.value,
                        old_values=old_values[1:],
                        new_values=None,
                        table=table,
                    )
                result = query(*args)
                if result is False:
                    return self.abort()
            return self.commit()
            
        except Exception as _:
            return self.abort()
    
    def _acquire_all_locks(self):
        """
        Acquire all necessary locks for the transaction (growing phase).
        """
        lock_manager = self.lock_manager_instance()
        
        for query, table, args in self.queries:
            query_name = getattr(query, '__name__', str(query))
            
            if query_name == 'insert':
                if not lock_manager.acquire_lock(self.transaction_id, id(table), -1, LockType.EXCLUSIVE):
                    return False
            else:
                record_id = args[0]
                lock_type = LockType.EXCLUSIVE if query_name in ['update', 'delete'] else LockType.SHARED
                if not lock_manager.acquire_lock(self.transaction_id, id(table), record_id, lock_type):
                    return False
        
        return True
    
    def abort(self):
        """
        Abort the transaction.
        """
        self.rollback()
        self.lock_manager_instance().release_locks(self.transaction_id)
        return False
    
    def rollback(self):
        for entry in reversed(self.log_manager_instance().entries):
            if entry.transaction_id == self.transaction_id:
                if entry.type == "insert":
                    # delete inserted
                    entry.table.index.indices[entry.table.key].remove(entry.key)
                    pass
                elif entry.type == "update":
                    # revert update
                    rids = entry.table.index.locate(0, entry.key)
                    entry.table.update_record(rids[0], [entry.key] + entry.old_values)
                    pass
                elif entry.type == "delete":
                    # insert deleted record
                    entry.table.create_record([entry.key] + entry.old_values)
                    pass
                elif entry.type == "commit":
                    return

    def commit(self):
        """
        Commit the transaction.
        """
        self.log_manager_instance().add(
            transaction_id=self.transaction_id,
            table_id=None,
            key=None,
            type="commit",
            old_values=None,
            new_values=None,
            table=None,
        )
        self.lock_manager_instance().release_locks(self.transaction_id)
        return True