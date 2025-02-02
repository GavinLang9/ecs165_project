
PAGE_SIZE = 4096
class Page:

    def __init__(self, record_size=8):
        self.num_records = 0
        self.record_size = record_size
        self.data = bytearray(PAGE_SIZE)

    def __getitem__(self, index: int) -> int:
        if index < 0 or index >= PAGE_SIZE / self.record_size:
            raise IndexError("index out of range")
        index = index * self.record_size
        byte_value = self.data[index: index + self.record_size]
        value = int.from_bytes(byte_value)
        return(value)
    
    def has_capacity(self) -> bool:
        return self.num_records * self.record_size < PAGE_SIZE
            

    def write(self, value) -> int:
        if not self.has_capacity():
            raise IndexError('Page is full')
        bytes = value.to_bytes(8)
        index = self.num_records * 8
        self.data[index: index + 8] = bytes
        self.num_records += 1
        return (self.num_records - 1)



