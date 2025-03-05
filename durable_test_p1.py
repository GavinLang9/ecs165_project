import pdb
from lstore.db import Database
from lstore.query import Query

db = Database()
db.open('./ECS165')
table = db.create_table('test', 5, 0)
num = 5

# print(table.page_directory)
query = Query(table)

for i in range(num):
  # if i == 512:
  #   pdb.set_trace()
  query.insert(*[i, i+1,i+1,i+1,i+1])
# print(query.table.page_directory)


for j in range(10):
  for i in range(num):
    # pdb.set_trace()
    query.update(i, *[i, None, None,i + j,None])
    print(query.select(i, 0, [1,1,1,1,1])[0])
  # print(len(db.tables[0].page_directory))

for i in range(num):
  record = query.select(i, 0, [1,1,1,1,1])[0]
  print(record.rid, record.indirection, record.schema_encoding, record.key, record.columns)
db.close()
pdb.set_trace()