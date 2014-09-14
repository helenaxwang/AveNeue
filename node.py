
class node(object):
    def __init__(self, value):
        self.value = value
        self.children = []

    def add_child(self, obj):
        self.children.append(obj)

    def add_all_children(self,values):
        for val in list(set(values)-set([self.value])):
            self.add_child(node(val))

    def __repr__(self, level=0):
        ret = " * "*level+repr(self.value)+"\n"
        for child in self.children:
            ret += child.__repr__(level+1)
        return ret

    #http://stackoverflow.com/questions/7134742/python-yield-all-paths-from-leaves-to-root-in-a-tree
    def paths(self, acc=[]):
        if self.value:
            yield acc+[self.value]
        for child in self.children:
            for leaf_path in child.paths(acc+[self.value]):
                yield leaf_path

    def flatten_tree(self):
        flattened = [self.value]
        children = self.children
        if children:
            for child in children:
                flattened.append(child.flatten_tree())
        return flattened                            


if __name__ == '__main__':
    n = node(5)
    p = node(6)
    q = node(7)
    n.add_child(p)
    n.add_child(q)
    p.add_child(node(8))
    print n
    print list(n.paths())
    print n.flatten_tree()

    # n2 = node(0)
    # n2.add_all_children([0,1,2,5])
    # print n

   