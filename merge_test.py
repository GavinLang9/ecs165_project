from lstore.db import Database
from lstore.query import Query

from random import choice, randint, sample, seed

db = Database()
# Create a table  with 5 columns
#   Student Id and 4 grades
#   The first argument is name of the table
#   The second argument is the number of columns
#   The third argument is determining the which columns will be primay key
#       Here the first column would be student id and primary key
grades_table = db.create_table('Grades', 5, 0)

# create a query class for the grades table
query = Query(grades_table)

# dictionary for records to test the database: test directory
records = {}

number_of_records = 9

for i in range(0, number_of_records):
    key = i

    records[key] = [key, randint(0, 20), randint(0, 20), randint(0, 20), randint(0, 20)]
    query.insert(*records[key])
    # print('inserted', records[key])
print("Insert finished")

for i in range(0,number_of_records):
    rec = grades_table.get_latest_record(i)
    #print(f'rid:{rec.rid}  key:{rec.key}  columns:{rec.columns}  base:{rec.base_rid}')
    print(f'rid:{rec.rid}  key:{rec.key}  columns:{rec.columns}')

for key in records:
    updated_columns = [None, None, None, None, None]
    for i in range(2, grades_table.num_columns):
        # updated value
        value = 123
        updated_columns[i] = value
        # copy record to check
        original = records[key].copy()
        # update our test directory
        records[key][i] = value
        query.update(key, *updated_columns)
        record = query.select(key, 0, [1, 1, 1, 1, 1])[0]
        updated_columns[i] = None

print("Update finished\n")


print("This test has 3 updates per record -> merge occurs every 15 updates \n-> 9 Total Records -> 27 updates -> 1 merge \n-> Output should display 5 newly merged base records and then 4 unupdated base records")
for i in range(0,number_of_records):
    rec = grades_table.get_record(i)
    print(f'rid:{rec.rid}  key:{rec.key}  columns:{rec.columns}')

print("\nThis Select output should display 5 newly merged base records and then 4 latest base records")
for i in range(0,number_of_records):
    #rec = grades_table.get_record(i)
    rec = query.select(i, 0, [1, 1, 1, 1, 1])[0]
    print(f'rid:{rec.rid}  key:{rec.key}  columns:{rec.columns}')
