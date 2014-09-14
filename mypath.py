import itertools
import numpy as np
#import collections
import pdb
from node import node
# http://stackoverflow.com/questions/6914803/python-iterator-through-tree-with-list-of-children

# http://stackoverflow.com/questions/2482602/a-general-tree-implementation-in-python
def build_tree(currloc=0,locations=[0,1,2]):
    #assert(nvisits <= len(locations))
    n = node(currloc)
    newlocs = list(set(locations)-set([n.value]))
    for val in newlocs:
        n.add_child(build_tree(val,newlocs))
    return n

# http://stackoverflow.com/questions/11570499/generate-all-leave-to-root-paths-in-a-dictionary-tree-in-python
# http://stackoverflow.com/questions/5671486/enumerating-all-paths-in-a-tree
# def paths(tree):
#     root = tree.value
#     rooted_paths = [[root]]
#     for subtree in tree.children:
#         useable = paths(subtree)
#         print useable
#         for path in useable:
#             rooted_paths.append([root]+path)
#     return rooted_paths

# TODO: make this faster by using iterators effectively
# Take into account initial point, flag in the other function
def find_best_path(distance_matrix,duration_matrix, nlocations, loc_duration):
    # number of destinations to visit
    # rows = origins, columns = destinations  
    nplaces = distance_matrix.shape[0]
    visit_paths = build_tree(0,range(nplaces))
    visit_paths = visit_paths.paths()

    min_cost = float('inf')
    min_path = []

    # iterate through route 
    for path in visit_paths: 
        if len(path) != nlocations:
            continue

        # subtract y index by 1 because origin point cannot serve as a destination    
        curr_path = [(p1,p2-1) for p1, p2 in zip(path, path[1:])]

        distance = np.array([distance_matrix[p] for p in curr_path]) # distance along the path 
        duration = np.array([duration_matrix[p] for p in curr_path]) # duration along the route

        dur      = np.array([loc_duration[p] for p in path])

        # compute the cumulative value in time -- so we can figure out when we'll get to a place  
        cumdur = np.cumsum(dur[:-1]+duration)
        cumdur = np.append(0,cumdur)
        # compute the location score as a function of time
        #score    = [1 for p in path]
        score = np.ones(nlocations)
        curr_cost = 100. /sum(distance) * sum(score) # TODO: this should be a weighted sum with respect to time!!!
        
        # iterate through until we find the best path 
        if curr_cost < min_cost:
            min_cost = curr_cost
            min_path = curr_path
            print 'MIN SELECTED', min_cost, 100. /sum(distance), sum(score), min_path
        #pdb.set_trace()
    return min_path

if __name__ == '__main__':
    
    def test1():
        import time
        t0 = time.time()
        n = build_tree(0,range(0,5))
        print n
        print time.time() - t0

    def test2():
        t1 = time.time()
        print list(n.paths())
        print time.time() - t1

    def test3():
        distance_matrix = np.array([[1.,2.,3.,4.], [5.,6.,7.,8.], [9.,10.,11.,12.], [13.,14.,15.,16.]])
        duration_matrix = np.array([[1.,2.,3.,4.], [5.,6.,7.,8.], [9.,10.,11.,12.], [13.,14.,15.,16.]])
        loc_duration = [2,1,1,1]
        find_best_path(distance_matrix,duration_matrix,4,loc_duration)

    test3()
