import itertools
import numpy as np
#import collections
import pdb
from node import node
import time
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
def find_best_path(distance_matrix,duration_matrix, nlocations, loc_duration, time_score, interval=30, init_time_secs=36000):

# distance_matrix: n+1 x n matrix, where rows correspond to origin, columns correspond to destination
# duration_matrix: n+1 x n matrix
# loc_duration: n+1 array, time spent at each place
# time_score: n+1 x 48 matrix, score at each location at each half hour interval

    # number of destinations to visit
    # rows = origins, columns = destinations  
    nplaces = distance_matrix.shape[0]
    visit_paths = build_tree(0,range(nplaces))
    visit_paths = visit_paths.paths()

    max_score = 0.0
    max_path = []

    # iterate through route 
    for path in visit_paths: 
        if len(path) != nlocations:
            continue

        # subtract y index by 1 because origin point cannot serve as a destination    
        curr_path = [(p1,p2-1) for p1, p2 in zip(path, path[1:])]

        # compute the time componnent: 
        dur_transit = np.array([duration_matrix[p] for p in curr_path]) # duration along the route
        dur_stopped = np.array([loc_duration[p] for p in path]) # duration while stopped at each point

        # compute the cumulative value in time -- so we can figure out when we'll get to a place  
        cumdur = np.cumsum(dur_stopped[:-1]+dur_transit)

        cumdur = np.append(0,cumdur)[:] + init_time_secs

        # go to the nearest interval 
        time_idx = np.floor(cumdur/(60*interval)).astype('int')
        time_idx = time_idx % (24 * (60/interval))

        if (time_idx[-1]-time_idx[0]) > 60/interval*24-1:
            print 'trip exceeds 24 hrs!'
            continue

        # print path, time_idx, time_score.shape
        # compute the location score as a function of time and location
        # time_score = [nlocs x ntimepts]
        curr_time_score = [time_score[(loc,hr)] for loc, hr in zip(path,time_idx)] 

        # distance along the path
        distance = np.array([distance_matrix[p] for p in curr_path]) 

        # get weighted score for this route 
        curr_score = (1. /sum(distance)) * sum(curr_time_score) 
        
        # iterate through until we find the best path 
        #print path, distance, sum(distance)
        if curr_score > max_score:
            max_score = curr_score
            max_path  = curr_path
            print 'MAX SELECTED', max_score, path, curr_path
        # else:
        #     print 'REJECTED', path, curr_path
        #pdb.set_trace()
    return max_path, time_idx

if __name__ == '__main__':
    
    def test1():
        t0 = time.time()
        n = build_tree(0,range(0,5))
        print n
        print time.time() - t0

    def test2():
        t1 = time.time()
        print list(n.paths())
        print time.time() - t1

    def test3():
        distance_matrix = np.arange(12).reshape((4,3)) 
        duration_matrix = np.ones((4,3))*3600
        loc_duration = np.array([1,1,1,1])*3600
        time_score = np.ones((4,48))
        min_path, time_idx = find_best_path(distance_matrix,duration_matrix,4,loc_duration,time_score)
        print min_path

    test3()
