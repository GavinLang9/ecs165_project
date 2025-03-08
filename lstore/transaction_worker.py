from lstore.table import Table, Record
from lstore.index import Index
import threading

class TransactionWorker:
    """
    # Creates a transaction worker object.
    Works with transactions that implement the Two-Phase Locking protocol.
    """
    def __init__(self, transactions = None):
        self.stats = []
        self.transactions = transactions if transactions is not None else []
        self.result = 0
        self.thread = None
    
    def add_transaction(self, t):
        """
        Appends t to transactions
        """
        self.transactions.append(t)
    
    def run(self):
        """
        Runs all transaction as a thread
        """
        self.thread = threading.Thread(target=self.__run)
        self.thread.start()
    
    def join(self):
        """
        Waits for the worker to finish
        """
        if self.thread:
            self.thread.join()
    
    def __run(self):
        for transaction in self.transactions:
            self.stats.append(transaction.run())
        self.result = len(list(filter(lambda x: x, self.stats)))