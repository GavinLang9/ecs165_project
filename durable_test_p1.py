import pdb
from lstore.db import Database
from lstore.query import Query

db = Database()
db.open('./ECS165')
table = db.create_table('test', 5, 0)
num = 1000

# print(table.page_directory)
query = Query(table)

for i in range(num):
  query.insert(*[i, i+1,i+1,i+1,i+1])
# print(query.table.page_directory)

for i in range(num):
  # pdb.set_trace()
  query.update(i, *[i, i+1,i+2,i+3,i+4])
# print(len(db.tables[0].page_directory))
pdb.set_trace()
db.close()
