from lstore.table import Table
from lstore.query import Query
from lstore.query import Index
import pdb

table = Table('test', 3, 0)

num = 10
query = Query(table)
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

success1 = query.insert(11, 12, 13)
# print(success1)
#table.create_record([10001, 2002, 3003])
rec = table.get_latest_record(10)
print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')

#success2 = query.insert(10002, 2002, 4003)
#table.create_record([10002, 2002, 4003])
success2 = query.insert(12, 13, 14)
rec = table.get_latest_record(11)
print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')
print(f"\n")

# Test Locate\
locate_records = query.index.indices[1].get(10)
print("USING INDEX LOCATE:")
print(f"RID's where column 1 is 2002: {locate_records}\n")
print(table.index.testPrint())
'''
# Test Select
select_records = query.select(2002, 1, [1, 1, 1])
print("USING SELECT:")
print(f"RID's where column 1 is 2002: {select_records}\n")
'''
