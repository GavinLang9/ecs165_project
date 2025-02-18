import pdb
from lstore.db import Database
from lstore.query import Query


new_db = Database()
pdb.set_trace()
new_db.open('./ECS165')

test_table = new_db.get_table('test')

test_query = Query(test_table)

for i in range(5):
  record = test_query.select(i, 0, [1,1,1,1,1])
  print(record)