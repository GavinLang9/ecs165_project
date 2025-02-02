from lstore.page import Page
from typing import List

PAGE_RANGE_MAX_LEN = 64


"""
PageRange
    - abstraction used for better code organization
    - collection of pages
    - has a max length of PAGE_RANGE_MAX_LEN
"""
class PageRange:
    def __init__(self, pages: List[Page]):
        if len(pages) > PAGE_RANGE_MAX_LEN:
            raise ValueError("PAGE_RANGE_MAX_LEN exceeded")
        self.pages: List[Page] = pages
        self.index: int = 0
        pass

    def __iter__(self):
        self.index = 0
        return self
    
    def __next__(self): 
        if self.index < len(self.pages):
            result = self.pages[self.index]
            self.index += 1
            return result
        else:
            raise StopIteration
        
    def __getitem__(self, index: int) -> Page:
        if index < 0 or index >= len(self.pages):
            raise IndexError("index out of range")
        return self.pages[index]

    def __len__(self):
        return len(self.pages)

"""
Disk
    - collection of page ranges
    - has no max length
"""
class Disk:
    def __init__(self):
        self.page_ranges: List[PageRange] = []
        pass

    def read(self, page_range_index: int, page_index: int):
        """
        Read a page from the disk
        If the page range index is out of range, raise an IndexError
        If the page index is out of range, raise an IndexError
        """
        if page_range_index < 0 or page_range_index >= len(self.page_ranges):
            raise IndexError("page_range_index out of range")
        
        page_range = self.page_ranges[page_range_index]

        if page_index < 0 or page_index >= len(page_range):
            raise IndexError("page_index out of range")
        
        return self.page_ranges[page_range_index][page_index]

    def write(self, page: Page):
        """
        Writes a page to the disk
        If the last page range is full, create a new page range
        Appends the page to the last page range
        """
        if self.page_ranges[len(self.page_ranges) - 1].index == PAGE_RANGE_MAX_LEN:
            self.page_ranges.append(PageRange([page]))

        self.page_ranges[len(self.page_ranges) - 1].pages.append(page)
