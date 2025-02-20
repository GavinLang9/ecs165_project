from typing import List, Tuple
"""
# Data Structure: Node
#  param: is_leaf: bool - True if node is a leaf node, False otherwise
#  param: t: int - Minimum degree of the B-Tree (minimum number of keys in a node)
#  keys: list - List of keys in the node - Tuple of (key, value)
#  children: list - List of children nodes (number of children is equal to number of keys + 1)
"""
class Node:
    def __init__(self, is_leaf: bool, t: int):
        self.is_leaf: bool = is_leaf
        self.t: int = t
        self.keys: List[Tuple] = []
        self.children: List[Node]  = []

    def binary_search(self, key: int) -> int:
        """
        Perform binary search to find the index of a key in the node.
        """
        low = 0
        high = len(self.keys) - 1
        
        while low <= high:
            mid = (low + high) // 2
            curr_key = self.keys[mid][0]
            
            if curr_key == key:
                return mid 
            elif curr_key < key:
                low = mid + 1
            else:
                high = mid - 1
        
        return low

    def get(self, key: int) -> Tuple:
        """
        Search for a key in the B-Tree
        # Traverse the tree from root to leaf
        # If the key is found, return the value
        # If the key is not found, return None
        # time complexity: O(log(n))
        # space complexity: O(1)
        """

        # Find the first key greater than or equal to the key
        i = self.binary_search(key)
        
        # Found the key in the node then return the value
        if i < len(self.keys) and key == self.keys[i][0]:
            return self.keys[i][1]
        
        # Key not found in the tree
        if self.is_leaf:
            return None
        
        # Key not found in node but node is not a leaf so search the child node
        return self.children[i].get(key)
    
    def get_range(self, pairs: List[int], start: int, end: int):
        """
        Sets the pairs list to be the in-order traversal of the B-Tree if the key is in the range [start, end]
        time complexity: O(log(n) + k)
        space complexity: O(k)
        """

        # Find the first key greater than or equal to the key
        i = self.binary_search(start)

        while i < len(self.keys) and self.keys[i][0] <= end:
            if not self.is_leaf:
                self.children[i].get_range(pairs, start, end)

            pairs.append(self.keys[i][1])
            i += 1

        if not self.is_leaf and i < len(self.children):
            self.children[i].get_range(pairs, start, end)

    def debug_display(self, level=0):
        """
        Traverse the B-Tree
        # Recursively traverse the left most child
        # Recursively traverse the right most child
        # Display the keys of the node
        """

        print(f"L{level}: {self.keys}")
        if not self.is_leaf:
            for child in self.children:
                child.debug_display(level + 1)
    def remove(self, key: int, tree):
        """
        Removes a key from the B-Tree.
        Ensures the tree remains balanced after removal.
        """
        i = self.binary_search(key)

        # Case 1: Key is in this node
        if i < len(self.keys) and self.keys[i][0] == key:
            if self.is_leaf:
                self.keys.pop(i)  # Direct removal from leaf
            else:
                self.remove_internal_node_key(i, tree)
        else:
            # Key is not in this node, find the correct child
            if self.is_leaf:
                return  # Key not found, nothing to do

            child = self.children[i]
            if len(child.keys) < self.t:
                self.ensure_valid_child(i, tree)
            
            # Recursive delete in the adjusted child node
            self.children[i].remove(key, tree)

    def remove_internal_node_key(self, idx: int, tree):
        """
        Handles deletion when the key is in an internal node.
        """
        if len(self.children[idx].keys) >= self.t:
            # Use predecessor (largest in left subtree)
            pred_key = self.get_predecessor(idx)
            self.keys[idx] = pred_key
            self.children[idx].remove(pred_key[0], tree)
        elif len(self.children[idx + 1].keys) >= self.t:
            # Use successor (smallest in right subtree)
            succ_key = self.get_successor(idx)
            self.keys[idx] = succ_key
            self.children[idx + 1].remove(succ_key[0], tree)
        else:
            # Merge children and remove recursively
            self.merge_children(idx)
            self.children[idx].remove(self.keys[idx][0], tree)

    def ensure_valid_child(self, idx: int, tree):
        """
        Ensures the child at index idx has enough keys for deletion.
        """
        if idx > 0 and len(self.children[idx - 1].keys) >= self.t:
            self.borrow_from_left(idx)
        elif idx < len(self.children) - 1 and len(self.children[idx + 1].keys) >= self.t:
            self.borrow_from_right(idx)
        else:
            if idx < len(self.children) - 1:
                self.merge_children(idx)
            else:
                self.merge_children(idx - 1)

    def get_predecessor(self, idx: int):
        """Finds the largest key in the left subtree (predecessor)."""
        node = self.children[idx]
        while not node.is_leaf:
            node = node.children[-1]
        return node.keys[-1]

    def get_successor(self, idx: int):
        """Finds the smallest key in the right subtree (successor)."""
        node = self.children[idx + 1]
        while not node.is_leaf:
            node = node.children[0]
        return node.keys[0]

    def borrow_from_left(self, idx: int):
        """
        Borrows a key from the left sibling.
        """
        child = self.children[idx]
        sibling = self.children[idx - 1]
        child.keys.insert(0, self.keys[idx - 1])  # Move parent's key down
        self.keys[idx - 1] = sibling.keys.pop()  # Move sibling's last key up

        if not sibling.is_leaf:
            child.children.insert(0, sibling.children.pop())

    def borrow_from_right(self, idx: int):
        """
        Borrows a key from the right sibling.
        """
        child = self.children[idx]
        sibling = self.children[idx + 1]
        child.keys.append(self.keys[idx])  # Move parent's key down
        self.keys[idx] = sibling.keys.pop(0)  # Move sibling's first key up

        if not sibling.is_leaf:
            child.children.append(sibling.children.pop(0))

    def merge_children(self, idx: int):
        """
        Merges the child at idx with its right sibling.
        """
        child = self.children[idx]
        sibling = self.children[idx + 1]
        child.keys.append(self.keys[idx])  # Move parent key down
        child.keys.extend(sibling.keys)  # Merge sibling's keys

        if not child.is_leaf:
            child.children.extend(sibling.children)  # Merge sibling's children

        self.keys.pop(idx)
        self.children.pop(idx + 1)

    
"""
Data Structure B-Tree
# param: t: int - Minimum degree of the B-Tree (minimum number of keys in a node)
# param: root: Node - Root node of the B-Tree
"""
class Btree:
    def __init__(self, t: int):
        self.root = Node(is_leaf=True, t=t)
        self.table = {}
        self.t = t

    def debug_display(self):
        """
        Display the B-Tree if it is not empty
        """

        if self.root:
            self.root.debug_display()
        else:
            raise ValueError("B-Tree is empty")

    def get(self, key: int) -> int:
        """
        Search for a key in the B-Tree and returns the corresponding value
        """
        if not key in self.table:
            return None
        
        return self.table.get(key)
    
    def get_range(self, start: int, end: int) -> List[int]:
        """
        Get all records in key order in the B-Tree
        """

        if not self.root:
            return []
        
        res = []
        self.root.get_range(res, start, end)
        return res

    def insert(self, key_value: Tuple):
        """
        If the root is full, split the root and create a new root
        Then insert the key-value pair into the non-full root
        param: key_value: Tuple - Key-value pair to be inserted
        """

        self.table[key_value[0]] = key_value[1]
        root = self.root
        if len(root.keys) == (2 * self.t) - 1:
            new_root = Node(t=self.t, is_leaf=False)
            new_root.children.append(self.root)
            self.split_child(new_root, 0)
            self.root = new_root
        self.insert_non_full(self.root, key_value)

    def insert_non_full(self, node: Node, key_value: Tuple):
        """
        Inset a key-value pair into a non-full node
        """
        idx = node.binary_search(key_value[0])

        if idx < len(node.keys) and node.keys[idx][0] == key_value[0]:
            # Key found, update the value
            node.keys[idx] = key_value
            return

        if node.is_leaf:
            node.keys.insert(idx, key_value)
        else:
            child = node.children[idx]
            if len(child.keys) == (2 * self.t) - 1:
                self.split_child(node, idx)
                if key_value[0] > node.keys[idx][0]:
                    idx += 1
            self.insert_non_full(node.children[idx], key_value)

    def split_child(self, parent: Node, i: int):
        """
        Split the child node of the parent node
        """

        t = self.t
        child = parent.children[i]
        new_child = Node(t=t, is_leaf=child.is_leaf)
        parent.keys.insert(i, child.keys[t - 1])
        parent.children.insert(i + 1, new_child)
        new_child.keys = child.keys[t:(2 * t - 1)]
        child.keys = child.keys[:t - 1]
        if not child.is_leaf:
            new_child.children = child.children[t:(2 * t)]
            child.children = child.children[:t]
    
    def remove(self, key: int):
        """
        Removes a key from the B-Tree.
        If the tree becomes empty after deletion, adjust the root.
        """
        if key not in self.table or not self.root:
            return

        self.table.pop(key)
        self.root.remove(key, self)

        # If the root becomes empty after removal, update root
        if len(self.root.keys) == 0:
            if self.root.is_leaf:
                self.root = None  # Tree is empty
            else:
                self.root = self.root.children[0]  # Make child the new root

    def merge_children(self, parent: Node, idx: int):
        """
        Merges two child nodes at index idx and idx+1 into one.
        """
        child = parent.children[idx]
        sibling = parent.children[idx + 1]
        child.keys.append(parent.keys[idx])  # Move key down
        child.keys.extend(sibling.keys)  # Merge sibling keys

        if not child.is_leaf:
            child.children.extend(sibling.children)  # Merge children

        parent.keys.pop(idx)
        parent.children.pop(idx + 1)