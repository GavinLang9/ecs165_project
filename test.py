# from lstore.page_range import PageRange

# page_range = PageRange(5)
# print(page_range.pages)

ba = bytearray(4096)

num = 1000
num_bytes = num.to_bytes(8)
ba[0:8] = num_bytes
print(ba)

number = int.from_bytes(num_bytes)
print(number)