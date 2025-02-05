from collections import OrderedDict
from lstore.disk import Disk
from lstore.page import Page
import os

class BufferPool:
    """
    The BufferPool manages loading and evicting pages from memory using LRU policy
    """
    def __init__(self, capacity: int, disk: Disk):
        self.capacity = capacity  # Number of pages that can be held in memory
        self.pool = OrderedDict()  # Maps (page_range_id, page_id) -> Page
        self.dirty_pages = set()   # Tracks which pages have been modified
        self.pin_count = {}
        self.disk = disk
        
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
            page = self.disk.read(page_range_id, page_id)
            
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
        self.force_page(page_range_id, page_id)

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
            self.disk.write(page)
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
                self.disk.write(page)
        self.dirty_pages.clear()

    def force_page(self, page_range_id, page_id):
        """
        Forces a page to be written back to disk immediately
        """
        key = (page_range_id, page_id)
        if key in self.pool and key in self.dirty_pages:
            self.disk.write(page_range_id, page_id, self.pool[key])
            self.dirty_pages.remove(key)

    def _is_full(self):
        return len(self.pool) >= self.capacity