from enum import Enum
from collections import defaultdict
import threading
import time

# 0 for reads, 1 for writes
class LockType(Enum):
    SHARED = 0 
    EXCLUSIVE = 1

class LockManager:
    """
    Manages locks for the database system.
    """
    def __init__(self):
        self.lock = threading.RLock() 
        self.locks = defaultdict(dict) 
        self.transaction_locks = defaultdict(list)
        self.waiting_for = defaultdict(set) 

    def acquire_lock(self, transaction_id, table_id, key, lock_type, timeout=100):
        """
        tries to acquire a lock
        """
        start_time = time.time()
        wait_event = threading.Event()
        
        while True:
            if time.time() - start_time > timeout:
                return False 
            
            with self.lock:
                if key in self.locks.get(table_id, {}):
                    record_locks = self.locks[table_id][key]
                    if transaction_id in record_locks:
                        current_lock = record_locks[transaction_id]
                        if current_lock == LockType.EXCLUSIVE or lock_type == LockType.SHARED:
                            return True

                # if lock can be granted
                if self._can_acquire_lock(transaction_id, table_id, key, lock_type):
                    if table_id not in self.locks:
                        self.locks[table_id] = {}
                    if key not in self.locks[table_id]:
                        self.locks[table_id][key] = {}
                    
                    self.locks[table_id][key][transaction_id] = lock_type
                    self.transaction_locks[transaction_id].append((table_id, key, lock_type))
                    self.waiting_for[transaction_id] = {}
                    return True
                
                self._update_waiting_for(transaction_id, table_id, key)
                
                if self._detect_deadlock(transaction_id):
                    self.waiting_for[transaction_id] = {}
                    return False
            
            wait_event.wait(timeout=0.01)
            wait_event.clear()
    
    def _can_acquire_lock(self, transaction_id, table_id, record_id, lock_type):
        """
        Checks if a lock can be acquired based on existing locks.
        """
        if record_id == -1:
            if table_id not in self.locks or -1 not in self.locks[table_id]:
                return True
            record_locks = self.locks[table_id][-1]
            return len(record_locks) == 0 or (len(record_locks) == 1 and transaction_id in record_locks)
        
        if table_id not in self.locks or record_id not in self.locks[table_id]:
            return True
        
        record_locks = self.locks[table_id][record_id]
        
        if transaction_id in record_locks:
            current_lock = record_locks[transaction_id]
            if current_lock == LockType.SHARED and lock_type == LockType.EXCLUSIVE:
                return len(record_locks) == 1 
            return True 
        
        # when requesting shared make sure no other transactions hold exclusive locks
        if lock_type == LockType.SHARED:
            return not any(lt == LockType.EXCLUSIVE for tid, lt in record_locks.items())
        
        # requesting exclusive lock
        return len(record_locks) == 0
    
    def _update_waiting_for(self, transaction_id, table_id, record_id):
        """
        Updates the waiting_for data structure for deadlock detection.
        """
        if table_id in self.locks and record_id in self.locks[table_id]:
            # This transaction is waiting for all transactions that hold locks on this record
            for tid in self.locks[table_id][record_id]:
                if tid != transaction_id:
                    self.waiting_for[transaction_id].add(tid)
    
    def _detect_deadlock(self, transaction_id, visited=None):
        """
        Detects deadlocks using cycle detection in wait-for graph.
        """
        if visited is None:
            visited = set()
        
        if transaction_id in visited:
            return True
        
        visited.add(transaction_id)
        
        for waiting_for_tid in self.waiting_for[transaction_id]:
            if self._detect_deadlock(waiting_for_tid, visited.copy()):
                return True
        
        return False
    
    def release_locks(self, transaction_id):
        """
        Releases all locks held by a transaction.
        """
        with self.lock:
            for table_id, record_id, _ in self.transaction_locks.get(transaction_id, []):
                if table_id in self.locks and record_id in self.locks[table_id]:
                    if transaction_id in self.locks[table_id][record_id]:
                        del self.locks[table_id][record_id][transaction_id]
                        
                        if not self.locks[table_id][record_id]:
                            del self.locks[table_id][record_id]
                        if not self.locks[table_id]:
                            del self.locks[table_id]
            
            if transaction_id in self.transaction_locks:
                del self.transaction_locks[transaction_id]
            if transaction_id in self.waiting_for:
                del self.waiting_for[transaction_id]