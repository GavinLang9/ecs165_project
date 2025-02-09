
from lstore.table import Table
import pdb
table = Table('test', 3, 0)

num = 10000

for i in range(0,num):
  table.create_record([i+1, i+1, i+1])


rid = 'rid'
key='key'
print(f'{rid:<{5}} {key:<{5}} columns\n')

for i in range(0,num, 1000):
  rec = table.get_latest_record(i)
  print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')

# print(table.disk)

print('\n')
for i in range(0,num):
  table.update_record(i, [None, i + 2, i + 3])

# print(table.disk)


print(f'{rid:<{5}} {key:<{5}} columns\n')

for i in range(0,num, 1000):
#   pdb.set_trace()
  rec = table.get_latest_record(i)
  print(f'{rec.rid:<{5}} {rec.key:<{5}} {rec.columns}')

# print(table.disk)
# tu = (None, None, 1, 0, None)
# l = sum(1 for x in tu if x is not None)
# print(l)

# up = list(0 for x in tu if x is not None else None)
# print(up)
#dd
