from lstore.table import Table
from lstore.query import Query
from lstore.query import Index
import pdb

table = Table('test', 3, 0)

num = 10
query = Query(table)

# Test Insert
for i in range(0,num):
  testInsert = query.insert(i+1, i+10, i+100)

rid = 'rid'
key = 'key'
print(f'{rid:<{5}} {key:<{5}} columns\n')

for i in range(0,num ):
  rec = table.get_latest_record(i)
  print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')

# print(table.disk)
"""
print('\n')
for i in range(0,num):
  table.update_record(i, [None, i + 2, i + 3])

# print(table.disk)


print(f'{rid:<{5}} {key:<{5}} columns\n')

for i in range(0,num, 1000):
#   pdb.set_trace()
  rec = table.get_latest_record(i)
  print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')
"""

success1 = query.insert(11, 19, 108)
# print(success1)
rec = table.get_latest_record(10)
print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')

success2 = query.insert(12, 18, 108)
rec = table.get_latest_record(11)
print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')
print(f"\n")

# Test Locate\
locate_column = 1
locate_key = 19
locate_records = query.index.indices[locate_column].get(locate_key)
print("USING INDEX LOCATE:")
print(f"RID's where column {locate_column} is {locate_key}: {locate_records}\n")

# Test Select
# select_records = query.select(locate_key, locate_column, [1, 1, 1])
# print("USING SELECT:")
# print(f"RID's where column {locate_column} is {locate_key}: {select_records}\n")
