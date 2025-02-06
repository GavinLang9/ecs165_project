from lstore.page import Page
from lstore.table import Table

table = Table("students", 3, 0)

for i in range(0,10000):

    table.create_record([i + 1,i + 1, i + 1])
    # print(table.bufferpool)

# for key in table.page_directory:
#   print(key, table.page_directory[key])

record = table.get_record(0)
print(record.rid, record.key, record.columns)

record = table.get_record(1)
print(record.rid, record.key, record.columns)

record = table.get_record(2)
print(record.rid, record.key, record.columns)

record = table.get_record(3)
print(record.rid, record.key, record.columns)
record = table.get_record(50)
print(record.rid, record.key, record.columns)

record = table.get_record(90)
print(record.rid, record.key, record.columns)

record = table.get_record(99)
print(record.rid, record.key, record.columns)

record = table.get_record(290)
print(record.rid, record.key, record.columns)

record = table.get_record(500)
print(record.rid, record.key, record.columns)

record = table.get_record(3490)
print(record.rid, record.key, record.columns)

record = table.get_record(5940)
print(record.rid, record.key, record.columns)


record = table.get_record(9998)
print(record.rid, record.key, record.columns)

record = table.get_record(9999)
print(record.rid, record.key, record.columns)




