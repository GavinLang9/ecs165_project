import pdb
from lstore.db import Database
from lstore.query import Query

db = Database()
db.open('./ECS165')
table = db.create_table('test', 5, 0)
# print(table.page_directory)
query = Query(table)

for i in range(5):
  query.insert(*[i, i+1,i+1,i+1,i+1])
# print(query.table.page_directory)
pdb.set_trace()

# print(len(db.tables[0].page_directory))

db.close()
