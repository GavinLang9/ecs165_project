import pdb
from lstore.config import *

class Page:
    def __init__(self, record_size=RECORD_SIZE):
        self.num_records = 0
        self.record_size = record_size
        self.data = bytearray(PAGE_SIZE)

    def __str__(self):
        s = ''
        for i in range(self.num_records):
            s += str(self.__getitem__(i))
            s += ' '
        return s

    def __getitem__(self, index: int) -> int:
        if index < 0 or index >= PAGE_SIZE / self.record_size:
            raise IndexError("index out of range")
        index = index * self.record_size
        byte_value = self.data[index: index + self.record_size]
        value = int.from_bytes(byte_value, byteorder='big')  # Added byteorder here
        return value

    def has_capacity(self) -> bool:
        return self.num_records * self.record_size < PAGE_SIZE

    def write(self, value) -> int:
        if not self.has_capacity():
            raise IndexError('Page is full')
        
        if type(value) != bytes:
            value = value.to_bytes(self.record_size, byteorder='big')  # Added byteorder here
        index = self.num_records * self.record_size
        self.data = bytearray(self.data)
        self.data[index: index + self.record_size] = value
        self.num_records += 1
        return (self.num_records - 1)

    def update(self, index, value):
        if type(value) != bytes:
            value = value.to_bytes(self.record_size, byteorder='big')  # Added byteorder here
            
        index = index * self.record_size
        self.data = bytearray(self.data)
        self.data[index: index + self.record_size] = value
        return True