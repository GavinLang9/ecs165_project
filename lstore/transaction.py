from lstore.table import Table, Record
from lstore.index import Index
from lstore.lock_manager import LockManager, LockType
from lstore.wal import WALManager, LogRecord

class Transaction:
    """
    # Creates a transaction object.
    Implements the Two-Phase Locking protocol with Write-Ahead Logging.
    """

    # shared lock manager among all instances
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
        self.queries = []  # list of queries associated with the transaction
        self.transaction_id = id(self)  # used to identify the transaction
        self.locks_acquired = False  # growing phase = True, shrinking phase = False
        self.wal_manager = WALManager.get_instance()
    
    def add_query(self, query, table, *args):
        """
        # Adds the given query to this transaction
        """
        self.queries.append((query, table, args))
    
    def run(self):
        """
        Runs the transaction with Two-Phase Locking protocol and WAL.
        Returns True if transaction commits or False on abort.
        """
        try:
            # acquire all locks
            if not self._acquire_all_locks():
                return self.abort()
            
            self.locks_acquired = True
            
            for query, table, args in self.queries:
                query_name = getattr(query, '__name__', str(query))
                
                # for each operation case
                if query_name == 'insert':
                    result = query(*args)
                    
                    if result is False:
                        return self.abort()
                    
                    log_record = LogRecord(
                        self.transaction_id,
                        query_name.upper(),
                        id(table),
                        record_id=args[0],
                        new_values=args
                    )
                    self.wal_manager.log(log_record)
                
                elif query_name in ['update', 'delete']:
                    record_id = args[0]
                    
                    # Get old values before modifying
                    old_record = None
                    if hasattr(table, 'select'):
                        old_record = table.select(record_id)
                    
                    # Log the operation
                    log_record = LogRecord(
                        self.transaction_id,
                        query_name.upper(),
                        id(table),
                        record_id=record_id,
                        old_values=old_record,
                        new_values=args
                    )
                    self.wal_manager.log(log_record)
                    
                    result = query(*args)
                    
                    if result is False:
                        return self.abort()
                
                else: 
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
            # Determine lock type based on operation
            query_name = getattr(query, '__name__', str(query))
            
            if query_name == 'insert':
                if not lock_manager.acquire_lock(
                    self.transaction_id, id(table), -1, LockType.EXCLUSIVE
                ):
                    return False
            elif len(args) > 0:
                record_id = args[0]
                lock_type = LockType.EXCLUSIVE if query_name in ['update', 'delete'] else LockType.SHARED
                
                if not lock_manager.acquire_lock(
                    self.transaction_id, id(table), record_id, lock_type
                ):
                    return False
        
        return True
    
    def abort(self):
        """
        Abort the transaction and rollback changes using WAL.
        Implements the shrinking phase of 2PL.
        """
        # Mark transaction as aborted in WAL
        self.wal_manager.mark_transaction_aborted(self.transaction_id)
        
        # Rollback using WAL records
        self._rollback_with_wal()
        
        # Release all locks (Phase 2: Shrinking phase)
        self.lock_manager_instance().release_locks(self.transaction_id)
        
        return False
    
    def commit(self):
        """
        Commit the transaction.
        Implements the shrinking phase of 2PL.
        """
        # Mark transaction as committed in WAL
        self.wal_manager.mark_transaction_committed(self.transaction_id)
        
        # Flush WAL to ensure durability
        self.wal_manager.flush()
        
        # Release all locks (Phase 2: Shrinking phase)
        self.lock_manager_instance().release_locks(self.transaction_id)
        
        return True
    
    def _rollback_with_wal(self):
        """
        Rollback transaction using WAL records
        """
        # Get all log records for this transaction
        log_records = self.wal_manager.get_transaction_logs(self.transaction_id)
        
        # Process in reverse order (LIFO) to correctly undo operations
        for record in reversed(log_records):
            try:
                if record.operation == "INSERT":
                    # Undo insert = delete
                    table = self._get_table_by_id(record.table_id)
                    if table and hasattr(table, 'delete'):
                        table.delete(record.record_id)
                
                elif record.operation == "UPDATE":
                    # Undo update = update with old values
                    table = self._get_table_by_id(record.table_id)
                    if table and hasattr(table, 'update') and record.old_values:
                        old_values = record.old_values.columns if hasattr(record.old_values, 'columns') else record.old_values
                        table.update(record.record_id, *old_values)
                
                elif record.operation == "DELETE":
                    # Undo delete = insert with old values
                    table = self._get_table_by_id(record.table_id)
                    if table and hasattr(table, 'insert_with_id') and record.old_values:
                        old_values = record.old_values.columns if hasattr(record.old_values, 'columns') else record.old_values
                        table.insert_with_id(record.record_id, *old_values)
            
            except Exception as e:
                print(f"Rollback error for {record}: {e}")
    
    def _get_table_by_id(self, table_id):
        """
        Helper method to find table object by its ID
        """
        for _, table, _ in self.queries:
            if id(table) == table_id:
                return table
        return None