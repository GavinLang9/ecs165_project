from collections import OrderedDict

class BufferPool:

  def __init__(self, capacity):
    self.pool = OrderedDict()
    self.pin_count = {}
    self.dirty = {}
    self.capacity = capacity # max number of pages that can be stored in bufferpool

