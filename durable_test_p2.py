import pdb
from lstore.db import Database
from lstore.query import Query


new_db = Database()
new_db.open('./ECS165')

num = 1000

test_table = new_db.get_table('test')

test_query = Query(test_table)
# pdb.set_trace()
for i in range(num):
  record = test_query.select(i, 0, [1,1,1,1,1])[0]
  print(record.rid, record.indirection, record.schema_encoding, record.key, record.columns)


for i in range(num):
  # pdb.set_trace()
  test_query.update(i, *[i, i+2,i+2,i+2,i+2])

for i in range(num):
  record = test_query.select(i, 0, [1,1,1,1,1])[0]
  print(record.rid, record.indirection, record.schema_encoding, record.key, record.columns)
