import unittest
from lstore.table import Table

class TestTable(unittest.TestCase):
    
    def test_create_record(self):
        table = Table('test', 5, 0)
        table.create_record()


if __name__ == '__main__':
    unittest.main()