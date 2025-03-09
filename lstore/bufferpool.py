import os
from collections import OrderedDict
import pdb
from lstore.page import Page
from lstore.config import *
class BufferPool:
    """
    The BufferPool manages loading and evicting pages from memory using LRU policy
    """

    def __init__(self, capacity: int, name: str, path: str):
        self.path = path
        self.table_name = name
        self.capacity = capacity  # Number of pages that can be held in memory
        self.pool = OrderedDict()  # Maps (page_range_id, page_id) -> Page
        self.dirty_pages = set()   # Tracks which pages have been modified
        self.pin_count = {}
        
        disk_path = os.path.join(self.path, DISK_DIRECTORY_PATH, f'{self.table_name}.bin')
        # Ensure the binary file exists
        if not os.path.exists(disk_path):
            open(disk_path, "x") 
                
    def __str__(self):
        s = ''
        for key in self.pool:
            page = self.pool[key]
            s += f'page range: {key[0]}\n'
            s += f'page: {key[1]}\n'
            s += f'num records: {page.num_records}\n\n'
            s += str(page)
            s += '\n\n'
        return s

    def get_page(self, page_range_id: int, page_id: int) -> Page:
        key = (page_range_id, page_id)
        self.pin_count[key] = self.pin_count.get(key, 0) + 1

        if key in self.pool:
            self.pool.move_to_end(key)
            self.pin_count[key] -= 1
            return self.pool[key]

        page = self._read_from_disk(page_range_id, page_id)
        if not page:
            self.pin_count[key] -= 1
            return None

        if self._is_full():
            self.evict_page()
        
        self.pool[key] = page
        self.pool.move_to_end(key)
        self.pin_count[key] -= 1
        return page

    def write_page(self, page_range_id: int, page_id: int, page: Page):
        try:
            key = (page_range_id, page_id)
            if key not in self.pool and self._is_full():
                self.evict_page()
            
            self.pool[key] = page
            self.mark_dirty(page_range_id, page_id)
        except Exception as e:
            
            print(f'error writing page to bufferpool: {e}')

        # self.force_page(page_range_id, page_id)

    def evict_page(self):
        try:
            if not self.pool:
                return
                
            key = None
            page = None
            
            items = list(self.pool.items())

            # Get least recently used page
            # Try to find first unpinned page
            for k, p in items:
                if k in self.pin_count and self.pin_count[k] == 0:
                    key, page = k, p
                    break
            else:
                # If all pages are pinned, we can't evict any
                raise Exception("All pages are pinned, cannot evict")
                        
            # If page was modified, write back to disk
            if key in self.dirty_pages:
                page_range_id = key[0]
                page_id = key[1]
                self._write_to_disk(page_range_id, page_id, page)
                self.dirty_pages.remove(key)

            self.pool.pop(key,None)
        except Exception as e:
            print(f'error in bufferpool evict page: {key}')

    def flush(self):
        for key, page in self.pool.items():
            if key in self.dirty_pages:
                self._write_to_disk(key[0], key[1], page)
        self.dirty_pages.clear()

    def force_page(self, page_range_id, page_id):
        key = (page_range_id, page_id)
        if key in self.pool and key in self.dirty_pages:
            self._write_to_disk(page_range_id, page_id, self.pool[key])
            self.dirty_pages.remove(key)

    def mark_dirty(self, page_range_id: int, page_id: int):
        try:
            key = (page_range_id, page_id)
            if key in self.pool:
                self.dirty_pages.add(key)
        except Exception as e:
            print(f'Error marking page {key} dirty')

    def _is_full(self):
        return len(self.pool) >= self.capacity

    def _write_to_disk(self, page_range_id, page_id, page):
        disk_path = os.path.join(self.path, DISK_DIRECTORY_PATH,  f'{self.table_name}.bin')

        offset = (page_range_id * PAGE_RANGE_MAX_LEN * PAGE_SIZE_WITH_META_DATA) + (page_id * PAGE_SIZE_WITH_META_DATA)
        num_records = page.num_records
        record_size = page.record_size

        page_data = num_records.to_bytes(8, byteorder='big') + \
            record_size.to_bytes(8, byteorder='big') + \
            page.data.ljust(PAGE_SIZE, b'\x00')
        
        if not os.path.exists(disk_path):
            open(disk_path, 'x')

        with open(disk_path, 'rb+') as disk:
            disk.seek(offset)
            disk.write(page_data)

    def _read_from_disk(self, page_range_id, page_id):
        offset = (page_range_id * PAGE_RANGE_MAX_LEN * PAGE_SIZE_WITH_META_DATA) + (page_id * PAGE_SIZE_WITH_META_DATA)
        disk_path = os.path.join(self.path, DISK_DIRECTORY_PATH, f'{self.table_name}.bin')
        if not os.path.exists(disk_path):
            # pdb.set_trace()
            open(disk_path, 'x')
        if os.path.getsize(disk_path) <= offset:
            return None
        try:
            with open(disk_path, 'rb') as disk:
                disk.seek(offset)
                bytes = disk.read(PAGE_SIZE + 16)
                num_records = int.from_bytes(bytes[0:8], byteorder='big')
                record_size = int.from_bytes(bytes[8:16], byteorder='big')
                if record_size == 0:
                    record_size = 8
                page = Page(record_size)
                page.data = bytes[16:]
                page.num_records = num_records
                return page
        except:
            return None
