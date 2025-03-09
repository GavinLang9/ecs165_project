import pdb
from lstore.table import Table, Record
from lstore.index import Index
from lstore.lock_manager import LockManager, LockType
import logging

logging.basicConfig(
    filename='transaction.log',
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
)
class Transaction:
    """
    # Creates a transaction object.
    Implements the Two-Phase Locking protocol.
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
        self.queries = [] # list of queries associated with the transaction
        self.transaction_id = id(self)  # used to identify the transaction
        self.locks_acquired = False  # growing phase = True, shrinking phase = False
        self.modified_records = []  # rollback: [(table, record_id, old_values)]
    
    def add_query(self, query, table, *args):
        """
        # Adds the given query to this transaction
        """
        self.queries.append((query, table, args))
    
    def run(self):
        """
        Runs the transaction with Two-Phase Locking protocol.
        Returns True if transaction commits or False on abort.
        """
        
        try:
            # acquire all locks
            logging.info(f"Thread {self.transaction_id} starting")
            if not self._acquire_all_locks():
                logging.warning(f"Thread {self.transaction_id} could not acquire all locks.  Aborting...")
                return self.abort()
            
            logging.info(f'Thread {self.transaction_id} acquired all locks')
            self.locks_acquired = True
            
            for query, table, args in self.queries:
                result = query(*args)
                
                # abort if any query fails
                if result is False: 
                    logging.error(f'Thread {self.transaction_id} failed query {query.__name__} on table {table.name} with args {args}.  Aborting...')
                    return self.abort()
                
                # track the newly inserted record
                if query.__name__ == 'insert' and result:
                    self.modified_records.append((table, result, None))
            
            logging.info(f'Thread {self.transaction_id} finished.  Committing now...')
            return self.commit()
        except IndexError as e:
            print(f'Index error: {e}')
            return self.abort()

        except KeyError as e:
            print(f'key Error: {e}')
            logging.error(f'Thread {self.transaction_id} aborted due to a key error.\n failed query {query.__name__} on table {table.name} with args {args}.  Aborting...')
            return self.abort()

        except Exception as e:
            print(f"Transaction error: {e}")
            logging.error(f'Thread {self.transaction_id} aborted due to an exception')
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
                # For inserts, we need to lock the table itself since we don't have a RID yet
                if not lock_manager.acquire_lock(
                    self.transaction_id, id(table), -1, LockType.EXCLUSIVE
                ):
                    return False
            elif len(args) > 0:
                # For other operations (update, delete, select)
                record_id = args[0]
                lock_type = LockType.EXCLUSIVE if query_name in ['update', 'delete'] else LockType.SHARED
                
                if not lock_manager.acquire_lock(
                    self.transaction_id, id(table), record_id, lock_type
                ):
                    return False
        
        return True
    
    def abort(self):
        """
        Abort the transaction and rollback changes.
        Implements the shrinking phase of 2PL.
        """
        # Rollback any changes that were made
        self._rollback()
        
        # Release all locks (Phase 2: Shrinking phase)
        self.lock_manager_instance().release_locks(self.transaction_id)
        
        return False
    
    def commit(self):
        """
        Commit the transaction.
        Implements the shrinking phase of 2PL.
        """
        # Release all locks (Phase 2: Shrinking phase)
        self.lock_manager_instance().release_locks(self.transaction_id)
        
        return True
    
    def _rollback(self):
        """
        Rollback all changes made by this transaction.
        """
        # This is a simple implementation. In a real system, you'd need a more robust
        # approach for rollback that uses logs
        for table, record_id, old_record in reversed(self.modified_records):
            try:
                if old_record is None:
                    # This was a new insert, so we need to delete it
                    query = getattr(table, 'delete', None)
                    if query:
                        query(record_id)
                else:
                    # This was an update, so restore old values
                    query = getattr(table, 'update', None)
                    if query:
                        # Extract columns from record for update
                        update_values = [col for col in old_record.columns]
                        query(record_id, *update_values)
            except Exception as e:
                print(f"Rollback error: {e}")