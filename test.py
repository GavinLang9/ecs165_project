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
columns = 'columns'
print(f'{rid:<{5}} {key:<{5}} columns\n')

for i in range(0, num):
  rec = table.get_latest_record(i)
  print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')

# Test Update
print('\n')
for i in range(1,num+1):
  query.update(i, None, i + 1000, i + 2000)
  #table.update_record(i, [None, i + 2000, i + 3000])

print(f'{rid:<{5}} {key:<{5}} columns & indirection\n')

for i in range(0, num):
  rec = table.get_latest_record(i)
  print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns} {rec.indirection}')

print('\n')
for i in range(1,num+1):
  query.update(i, None, i + 1000, i + 2000)
  #table.update_record(i, [None, i + 2000, i + 3000])

print(f'{rid:<{5}} {key:<{5}} columns & indirection\n')

for i in range(0, num):
  rec = table.get_latest_record(i)
  print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns} {rec.indirection}')

# Insert Records Matching Values
success1 = query.insert(21, 1010, 2010)
rec = table.get_latest_record(30)
print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')
success2 = query.insert(22, 18, 108)
rec = table.get_latest_record(31)
print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')
print(f"\n")

# Test Locate\
locate_column = 1
locate_key = 1010
locate_records = query.index.indices[locate_column].get(locate_key)
print("USING INDEX LOCATE:")
print(f"BASE RID's where column {locate_column} is {locate_key}: {locate_records}\n")

# Test Select
select_records = query.select(locate_key, locate_column, [1, 1, 1])
print("USING SELECT:")
print(f'{rid:<{5}} {key:<{5}} columns\n')
for rec in select_records:
  print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')

print(f"\n")

# Test Select Version
select_ver_records = query.select_version(locate_key, locate_column, [1, 1, 1], -3)
print("USING SELECT VERSION:")
print(f'{rid:<{5}} {key:<{5}} columns\n')
for rec in select_ver_records:
  print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')
