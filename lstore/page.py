class Page:

    def __init__(self):
        self.num_records = 0
        self.data = bytearray(4096)
        self.max_records = 512  # Assuming each record takes 8 bytes (64-bit integers)

    def has_capacity(self):
        return self.num_records < self.max_records

    def write(self, value):
        if not self.has_capacity():
            return False
        
        # Write value as 64-bit integer
        value_bytes = value.to_bytes(8, byteorder='big', signed=True)
        offset = self.num_records * 8
        self.data[offset:offset + 8] = value_bytes
        self.num_records += 1
        return True

    def read(self, index):
        if index >= self.num_records:
            return None
        
        offset = index * 8
        value_bytes = self.data[offset:offset + 8]
        return int.from_bytes(value_bytes, byteorder='big', signed=True)

