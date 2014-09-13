import itertools
import numpy as np
#import collections
import pdb

# TODO: make this faster by using iterators effectively
# Take into account initial point, flag in the other function
def find_best_path(distance_matrix,duration_matrix, loc_duration, loc_score):
    # number of destinations to visit
    # rows = origins, columns = destinations  
    nplaces = distance_matrix.shape[1]

    # arranged as N-1 elements starting at first location
    # N-2 elements starting at second location, N-3 elements at third...
    # Up till N-1 element as origin 
    pairwise_path = list(itertools.permutations(range(0,nplaces),2))

    # place_lists = []
    # for i in range(nplaces):
    #     curr_list = i * (nplaces-1) + np.array(range(nplaces-1))
    #     place_lists.append(curr_list)
    # print place_lists
    place_lists = range(len(pairwise_path))

    # get all possible combinations of pairwise paths
    # this assumes paths are symmetric about the diagonal 
    # place_lists = []
    # init = 0
    # for i in range(1,nplaces):
    #     curr_list = range(init,init+nplaces-i)
    #     #print i, curr_list
    #     init = curr_list[-1]+1
    #     place_lists.append(curr_list)
    #
    # A = range(0,nplaces-1) # indexing start 1 
    # B = range(A[-1]+1,(A[-1]+1)+nplaces-2) #indexing start 2
    # C = range(B[-1]+1,(B[-1]+1)+nplaces-3) #indexing start 3
    # place_lists = [A, B, C]

    # each number in each tuple is a pairwise path
    selected_places = list(itertools.permutations(place_lists, nplaces))
    #selected_places = list(itertools.product(*place_lists))
    print '# of permuations ', len(selected_places)

    min_cost = float('inf')
    min_path = []
    # iterate through route 
    for path in selected_places: 
        pairwise_idx = [pairwise_path[step] for step in path] # index for path
        
        # convert to array to check for feasibility 
        pairwise_idx_array = np.array(pairwise_idx) 
        start_pts = pairwise_idx_array[:,0]
        end_pts = pairwise_idx_array[:,1]
        #pdb.set_trace()
        if (np.any(start_pts[1:] != end_pts[:pairwise_idx_array.shape[0]-1])) or \
            (len(start_pts) > len(set(start_pts)) or len(end_pts) > len(set(end_pts))):
            #print 'rejected path', pairwise_idx
            #pdb.set_trace()
            continue
        
        #pdb.set_trace()
        distance = [distance_matrix[d] for d in pairwise_idx] # distance along the path 
        duration = [duration_matrix[d] for d in pairwise_idx] # duration along the route
        dur   = [loc_duration[s] for s in start_pts]
        score = [loc_score[s] for s in start_pts]

        curr_cost = sum(distance) # TODO: this should be a weighted sum with respect to time!!!
        #pdb.set_trace()
        # iterate through until we find the best path 
        if curr_cost < min_cost:
            min_cost = curr_cost
            min_path = pairwise_idx
            print min_cost, min_path
        else:
            print pairwise_idx
    #pdb.set_trace()
    return min_path
