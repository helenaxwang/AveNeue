import itertools
import numpy as np
#import collections
import pdb
import time

def find_best_path(distance_matrix,duration_matrix, nlocations, loc_duration, \
    time_score, interval=30, init_time_secs=36000):

# distance_matrix: n+1 x n matrix, where rows correspond to origin, columns correspond to destination
# duration_matrix: n+1 x n matrix
# loc_duration: n+1 array, time spent at each place
# time_score: n+1 x 48 matrix, score at each location at each half hour interval

    # number of destinations to visit
    # rows = origins, columns = destinations  
    nplaces = distance_matrix.shape[0] # total number of possible locations 
    # all permutations of visiting nlocations out of nplaces [0 = origin]
    visit_paths = itertools.permutations(range(1,nplaces), nlocations)

    max_score = 0.0
    max_path = []

    #t0 = time.time()
    # iterate through route 
    for path in visit_paths: 
        
        # split iterator
        path0, path1 = itertools.tee(path)
        # make into a list paths 
        curr_path = [ tuple(p) for p in itertools.izip( path0, itertools.islice(path1,1,None)) ]
        
        # add the initial step
        curr_path = [(0, curr_path[0][0])] + curr_path

        # compute the time componnent: 
        dur_transit = np.array([duration_matrix[(p[0],p[1]-1)] for p in curr_path]) # duration along the route
        dur_stopped = np.array([loc_duration[p] for p in path]) # duration while stopped at each point
        dur_stopped = np.insert(dur_stopped,0,0) # add zero for initial point 

        # compute the cumulative value in time -- so we can figure out when we'll get to a place  
        cumdur = np.cumsum(dur_stopped[:-1]+dur_transit)

        # account for starting time 
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
        curr_time_score = [time_score[(loc,hr)] for loc, hr in zip(path,time_idx[1:])] 

        # distance along the path
        distance = np.array([distance_matrix[(p[0],p[1]-1)] for p in curr_path]) 

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
    #print 'traverse through tree: ', time.time() - t0
    # change the indexing for y to account for the fact you can't go back to the origin 
    # so max_path_idx reflects indices for items in the distances matrix
    max_path_idx = [(p[0],p[1]-1) for p in max_path]
    return max_path_idx, time_idx


if __name__ == '__main__':

    def test1():
        places = range(5)
        t0 = time.time()
        places = itertools.permutations(places,5)
        #print places 
        print time.time() - t0, len(list(places))

    def test2():
        t0 = time.time()
        nlocations = 9;
        nvisits = 4;
        print 'visiting %d out of %d locations' % (nvisits, nlocations)
        distance_matrix = np.arange(nlocations*(nlocations+1)).reshape((nlocations+1,nlocations)) 
        duration_matrix = np.ones((nlocations+1,nlocations))*3600
        loc_duration = np.array(range(nlocations+1))*3600
        time_score = np.ones((nlocations+1,48))
        
        min_path, time_idx = find_best_path(distance_matrix,duration_matrix,nvisits,loc_duration,time_score)
        print min_path, time_idx
        print time.time() - t0, 's'

    print 'test 1..... '
    test1()
    
    print 'test 2..... '
    test2()
