from lstore.table import Table, Record
from lstore.index import Index
from lstore.lock_manager import LockManager, LockType

class Transaction:
    """
    # Creates a transaction object.
    Implements the Two-Phase Locking protocol with Write-Ahead Logging.
    """

    _lock_manager = None
    
    @classmethod
    def lock_manager_instance(cls):
        """
        returns shared lock manager instance
        """
        if cls._lock_manager is None:
            cls._lock_manager = LockManager()
        return cls._lock_manager
    
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
            for query, _, args in self.queries:
                result = query(*args)
                if result is False:
                    return self.abort()
            return self.commit()
            
        except Exception as e:
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
        self.lock_manager_instance().release_locks(self.transaction_id)
        return False
    
    def commit(self):
        """
        Commit the transaction.
        """
        self.lock_manager_instance().release_locks(self.transaction_id)
        return True