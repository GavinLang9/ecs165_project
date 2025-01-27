
PAGE_SIZE = 4096
class Page:

    def __init__(self, record_size=8):
        self.num_records = 0
        self.record_size = record_size
        self.data = bytearray(PAGE_SIZE)

    def has_capacity(self):
        if self.num_records * self.record_size < PAGE_SIZE:
            return True
        return False

    def write(self, value):
        bytes = value.to_bytes(8)
        index = self.num_records * 8
        self.data[index: index + 8] = bytes
        self.num_records += 1
        return index

