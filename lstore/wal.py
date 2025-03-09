from lstore.table import Table, Record

import time
import json
import struct
import os

class LogRecord:
    """
    Represents a single log record in the Write-Ahead Log
    """
    def __init__(self, transaction_id, operation, table_id, record_id=None, old_values=None, new_values=None):
        self.transaction_id = transaction_id
        self.operation = operation 
        self.table_id = table_id
        self.record_id = record_id
        self.old_values = old_values
        self.new_values = new_values
        self.timestamp = time.time()
    
    def serialize(self):
        """
        Serialize the log record using struct and JSON
        """
        old_values_json = json.dumps(self._prepare_for_json(self.old_values))
        new_values_json = json.dumps(self._prepare_for_json(self.new_values))
        
        record_dict = {
            "transaction_id": self.transaction_id,
            "operation": self.operation,
            "table_id": self.table_id,
            "record_id": self.record_id,
            "old_values": old_values_json,
            "new_values": new_values_json,
            "timestamp": self.timestamp
        }
        
        record_json = json.dumps(record_dict)
        
        return struct.pack("!I", len(record_json)) + record_json.encode('utf-8')
    
    @staticmethod
    def deserialize(data):
        """
        Deserialize a log record from bytes
        """
        length = struct.unpack("!I", data[:4])[0]
        
        record_json = data[4:4+length].decode('utf-8')
        record_dict = json.loads(record_json)
        
        log_record = LogRecord(
            record_dict["transaction_id"],
            record_dict["operation"],
            record_dict["table_id"],
            record_dict["record_id"],
            LogRecord._restore_from_json(json.loads(record_dict["old_values"])),
            LogRecord._restore_from_json(json.loads(record_dict["new_values"]))
        )
        log_record.timestamp = record_dict["timestamp"]
        
        return log_record
    
    @staticmethod
    def _prepare_for_json(value):
        """
        Prepare a value for JSON serialization
        """
        if value is None:
            return None
        
        if isinstance(value, Record):
            return {
                "__type__": "Record",
                "columns": value.columns
            }
        
        if isinstance(value, (list, tuple)):
            return list(value)
        
        return value
    
    @staticmethod
    def _restore_from_json(value):
        """
        Restore a value from its JSON representation
        """
        if value is None:
            return None
        
        # Handle Record objects
        if isinstance(value, dict) and value.get("__type__") == "Record":
            columns = value.get("columns", [])
            return Record(columns)
        
        return value
    
    def __str__(self):
        return f"LogRecord(txn={self.transaction_id}, op={self.operation}, table={self.table_id}, record={self.record_id})"


class WALManager:
    _instance = None
    
    @classmethod
    def get_instance(cls, log_dir="./logs"):
        if cls._instance is None:
            cls._instance = WALManager(log_dir)
        return cls._instance
    
    def __init__(self, log_dir="./logs"):
        self.log_dir = log_dir
        self.current_log_file = None
        self.log_buffer = []
        self.buffer_size_limit = 100
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self._initialize_log_file()
    
    def _initialize_log_file(self):
        """
        Creates a new log file with a timestamp-based name
        """
        timestamp = int(time.time())
        self.current_log_file = os.path.join(self.log_dir, f"wal_{timestamp}.log")
        
        if not os.path.exists(self.current_log_file):
            with open(self.current_log_file, 'wb') as f:
                pass 
    
    def log(self, log_record):
        """
        Adds a log record to the buffer and flushes if necessary
        """
        self.log_buffer.append(log_record)
        
        if len(self.log_buffer) >= self.buffer_size_limit:
            self.flush()
    
    def flush(self):
        """
        Writes all buffered log records to disk
        """
        if not self.log_buffer:
            return
        
        try:
            with open(self.current_log_file, 'ab') as f:
                for record in self.log_buffer:
                    # Serialize the log record
                    serialized = record.serialize()
                    f.write(serialized)
                f.flush()
                os.fsync(f.fileno())
            
            # Clear the buffer
            self.log_buffer.clear()
        except Exception as e:
            print(f"Error flushing WAL: {e}")
    
    def get_transaction_logs(self, transaction_id):
        """
        Retrieves all log records for a specific transaction
        """
        transaction_logs = []
        
        for record in self.log_buffer:
            if record.transaction_id == transaction_id:
                transaction_logs.append(record)
        
        try:
            if os.path.exists(self.current_log_file):
                with open(self.current_log_file, 'rb') as f:
                    while True:
                        size_bytes = f.read(4)
                        if not size_bytes or len(size_bytes) < 4:
                            break                          
                        size = struct.unpack("!I", size_bytes)[0]
                        
                        json_bytes = f.read(size)
                        if not json_bytes or len(json_bytes) < size:
                            break 
                        
                        record = LogRecord.deserialize(size_bytes + json_bytes)
                        
                        if record.transaction_id == transaction_id:
                            transaction_logs.append(record)
        except Exception as e:
            print(f"Error reading WAL: {e}")
        
        return transaction_logs
    
    def mark_transaction_committed(self, transaction_id):
        """
        Writes a commit record for the transaction
        """
        commit_record = LogRecord(transaction_id, "COMMIT", None)
        self.log(commit_record)
        self.flush()
    
    def mark_transaction_aborted(self, transaction_id):
        """
        Writes an abort record for the transaction
        """
        abort_record = LogRecord(transaction_id, "ABORT", None)
        self.log(abort_record)
        self.flush()
