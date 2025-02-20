from collections import OrderedDict
from lstore.disk import Disk
from lstore.page import Page
from lstore.config import *
import os

class BufferPool:
    """
    The BufferPool manages loading and evicting pages from memory using LRU policy
    """
    def __init__(self, capacity: int, name: str):
        self.path = ''
        self.table_name = name
        self.capacity = capacity  # Number of pages that can be held in memory
        self.pool = OrderedDict()  # Maps (page_range_id, page_id) -> Page
        self.dirty_pages = set()   # Tracks which pages have been modified
        self.pin_count = {}
        
    def __str__(self):
        s = ''
        for page_range_id, page_id in self.pool:
            key = (page_range_id, page_id)

            s += (f'page range {page_range_id}, page {page_id}: \n')
            for i in range(512):
                s += str(self.pool[key][i])
                s += ' '
            s += '\n'
        return s

    def get_page(self, page_range_id: int, page_id: int) -> Page:
        """
        Retrieves a page from the buffer pool. If not in memory, loads it from disk.
        Returns None if page doesn't exist.
        """
        key = (page_range_id, page_id)

        if key not in self.pin_count:
            self.pin_count[key] = 0
        self.pin_count[key] += 1
        
        # Check if page is in memory
        if key in self.pool:
            # Move to end to show it was recently used
            self.pool.move_to_end(key)
            self.pin_count[key] -= 1

            return self.pool[key]
        
        try:
            # Load page from disk
            page = self.read_from_disk(page_range_id, page_id)
            
            # If buffer pool is at capacity, evict least recently used page
            if self._is_full():
                # print('trying to evict page in reading')
                self.evict_page()
                
            # Add new page to pool
            self.pool[key] = page
            self.pool.move_to_end(key)
            self.pin_count[key] -= 1
            return page
            
        except IndexError:
            self.pin_count[key] -= 1
            return None

    def write_page(self, page_range_id: int, page_id: int, page: Page):
        key = (page_range_id, page_id)

        if key not in self.pool and self._is_full():
            # print('trying to evict page in writing')
            self.evict_page()

        self.pool[key] = page
        self.mark_dirty(page_range_id, page_id)

    def evict_page(self):
        """
        Removes the least recently used page from the buffer pool if it is not pinned.
        If page is dirty, writes it back to disk first.
        """
        if not self.pool:
            return
            
        key = None
        page = None
        
        # Get least recently used page
        # Try to find first unpinned page
        for k, p in self.pool.items():
            if self.pin_count[k] == 0:
                key, page = k, p
                break
        else:
            # If all pages are pinned, we can't evict any
            raise Exception("All pages are pinned, cannot evict")
                    
        # If page was modified, write back to disk
        if key in self.dirty_pages:
            page_range_id = key[0]
            page_id = key[1]
            self.write_to_disk(page_range_id, page_id, page)
            self.dirty_pages.remove(key)

        self.pool.pop(key)

    def mark_dirty(self, page_range_id: int, page_id: int):
        """
        Marks a page as dirty, meaning it needs to be written back to disk on eviction
        """
        key = (page_range_id, page_id)
        if key in self.pool:
            self.dirty_pages.add(key)

    def flush(self):
        """
        Writes all dirty pages back to disk
        Call this in higher level code (table) to write update pages to disk 
        """
        for key, page in self.pool.items():
            if key in self.dirty_pages:
                page_range_id = key[0]
                page_id = key[1]
                self.write_to_disk(page_range_id, page_id, page)
        self.dirty_pages.clear()

    def force_page(self, page_range_id, page_id):
        """
        Forces a page to be written back to disk immediately
        """
        key = (page_range_id, page_id)
        if key in self.pool and key in self.dirty_pages:
            self.write_to_disk(page_range_id, page_id, self.pool[key])
            self.dirty_pages.remove(key)

    def _is_full(self):
        return len(self.pool) >= self.capacity
    
    def read_from_disk(self, page_range_id: int, page_id: int) -> Page:
        """
        constructs page from bytes on disk.  If no page has been created, returns none
        """
        start_index = page_range_id * PAGE_RANGE_MAX_LEN * (PAGE_SIZE + 16) + page_id * (PAGE_SIZE + 16)
        disk_path = os.path.join(self.path, f'{self.table_name}.bin')
        if not os.path.exists(disk_path):
            open(disk_path, 'x')
        if os.path.getsize(disk_path) <= start_index:
            return None
        try:
            with open(disk_path, 'rb') as disk:
                disk.seek(start_index)
                bytes = disk.read(PAGE_SIZE + 16)
                num_records = int.from_bytes(bytes[0:8], byteorder='big')
                record_size = int.from_bytes(bytes[8:16], byteorder='big')
                page = Page(record_size)
                page.data = bytes[16:]
                page.num_records = num_records
                return page
        except:
            return None

    def write_to_disk(self, page_range_id: int, page_id, page: int):
        """
        writes a page to a specific offset in disk
        """
        disk_path = os.path.join(self.path, f'{self.table_name}.bin')
        start_index = page_range_id * PAGE_RANGE_MAX_LEN * (PAGE_SIZE + 16) + page_id * (PAGE_SIZE + 16)
        num_records = page.num_records
        record_size = page.record_size

        page_data = num_records.to_bytes(8, byteorder='big') + \
            record_size.to_bytes(8, byteorder='big') + \
            page.data
        
        if not os.path.exists(disk_path):
            open(disk_path, 'x')

        with open(disk_path, 'rb+') as disk:
            disk.seek(start_index)
            disk.write(page_data)
            