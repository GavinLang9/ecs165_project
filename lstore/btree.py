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

    def search(self, key: int) -> Tuple:
        """
        Search for a key in the B-Tree
        # Traverse the tree from root to leaf
        # If the key is found, return the value
        # If the key is not found, return None
        """

        # Find the first key greater than or equal to the key
        i = 0
        while i < len(self.keys) and key > self.keys[i][0]:
            i += 1
        
        # Found the key in the node then return the value
        if i < len(self.keys) and key == self.keys[i][0]:
            return self.keys[i][1]
        
        # Key not found in the tree
        if self.is_leaf:
            return None
        
        # Key not found in node but node is not a leaf so search the child node
        return self.children[i].search(key)
    
    def get_all_pairs(self):
        """
        Return the key value pairs of the node and its children
        """

        if self.is_leaf:
            return self.keys

        pairs = self.keys
        for child in self.children:
            pairs.extend(child.get_all_pairs())
        
        return pairs
    
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
    
"""
Data Structure B-Tree
# param: t: int - Minimum degree of the B-Tree (minimum number of keys in a node)
# param: root: Node - Root node of the B-Tree
"""
class BTree:
    def __init__(self, t: int):
        self.root = Node(is_leaf=True, t=t)
        self.t = t

    def debug_display(self):
        """
        Display the B-Tree if it is not empty
        """

        if self.root:
            self.root.debug_display()
        else:
            raise ValueError("B-Tree is empty")

    def search(self, key: int) -> int:
        """
        Search for a key in the B-Tree and returns the corresponding value
        """
        if not self.root:
            return None
        
        return self.root.search(key)
    
    def get_all_pairs(self):
        """
        Get all key-value pairs in the B-Tree
        """

        if not self.root:
            return []
        
        return self.root.get_all_pairs()

    def insert(self, key_value: Tuple):
        """
        If the root is full, split the root and create a new root
        Then insert the key-value pair into the non-full root
        param: key_value: Tuple - Key-value pair to be inserted
        """

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

        if node.is_leaf:
            node.keys.append(key_value)
            node.keys.sort()
        else:
            i = len(node.keys) - 1
            while i >= 0 and key_value[0] < node.keys[i][0]:
                i -= 1
            i += 1
            if len(node.children[i].keys) == (2 * self.t) - 1:
                self.split_child(node, i)
                if key_value[0] > node.keys[i][0]:
                    i += 1
            self.insert_non_full(node.children[i], key_value)

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
    
    
    
    

# Example Usage:
if __name__ == "__main__":
    b_tree = BTree(3)  # B-Tree of minimum degree 3
    
    keys = [(10, 1), (20, 1), (5, 6), (6, 2), (12, 100), (30, 1), (7, 3), (17, 4)]
    for val in keys:
        b_tree.insert(val)
    print("Traversal of B-tree:")
    b_tree.debug_display()
    print("\nSearch result for key 6:", "Found" if b_tree.search(6) else "Not Found")

    print("\nAll key-value pairs in B-Tree:")
    print(b_tree.get_all_pairs())

