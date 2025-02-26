from lstore.db import Database
from lstore.query import Query
from random import randint, seed

# Initialize database
db = Database()
grades_table = db.create_table('Grades', 5, 0)
query = Query(grades_table)

# Seed for reproducibility
seed(3562901)

# Insert 15 records
records = {}
for i in range(5000):
    key = 92106429 + randint(0, 10000)
    
    # Ensure unique keys
    while key in records:
        key = 92106429 + randint(0, 10000)

    records[key] = [key, randint(0, 20), randint(0, 20), randint(0, 20), randint(0, 20)]
    query.insert(*records[key])

print("15 records inserted.")

# Choose a key to update
update_key = list(records.keys())[5]  # Updating the 6th inserted record
updated_columns = [None, None, 99, None, 88]  # Updating only columns 2 and 4
updated_record = records[update_key].copy()
updated_record[2] = 99
updated_record[4] = 88

# Perform update
query.update(update_key, *updated_columns)
print(f"Updated record {update_key}: {updated_columns}")

# Verify update
record = query.select(update_key, 0, [1, 1, 1, 1, 1])[0]
error = False
for i, column in enumerate(record.columns):
    if column != updated_record[i]:
        error = True

if error:
    print(f"Update error on {update_key}: {record.columns}, expected: {updated_record}")
else:
    print(f"Update verified successfully for record {update_key}: {record.columns}")