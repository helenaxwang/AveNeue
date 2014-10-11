import urllib, json
import pymysql as mdb
import pprint
import pdb
import numpy as np

# format query and look up using google geocoding API
def get_google_address(address):
    #google_api_key = 'AIzaSyAfaYz3fgaT4GA2rLb_iF3nbpUoo8-e1Ss'
    google_api_key = 'AIzaSyDL3SBSFF2bwdvRjr6NaTW6iUH5Dwr53_g'
    address_formatted = '+'.join(address.split(' '))
    base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    address_request = 'address=' + address_formatted
    api_request = '&key=' + google_api_key
    complete_url = base_url + address_request + api_request 
    #print complete_url

    googleResponse = urllib.urlopen(complete_url)
    jsonResponse = json.loads(googleResponse.read())
    if jsonResponse['status'] == 'OK':
        results = jsonResponse['results']
        if len(results) > 1:
            print 'Warning, more than one result returned!!!!'
    else:
        print jsonResponse['status']
        results = None
    return results

# https://developers.google.com/places/documentation/search
def get_google_places(lat,lng,radius=10):
    google_api_key = 'AIzaSyAfaYz3fgaT4GA2rLb_iF3nbpUoo8-e1Ss'
    base_url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?'
    location_request = 'location=%s,%s' %(lat,lng)
    radius_request = '&radius=%d' % radius
    api_request = '&key=' + google_api_key
    complete_url = base_url + location_request + radius_request + api_request
    
    googleResponse = urllib.urlopen(complete_url)
    jsonResponse = json.loads(googleResponse.read())
    if jsonResponse['status'] == 'OK':
        results = jsonResponse['results']
        print 'Google Place search, %d results returned' % len(results)
    else:
        print jsonResponse['status']
        results = []
    return results


# format query and look up using google geocoding API
def get_google_direction_matrix(locations,origin=None,mode='walking'):
    google_api_key = 'AIzaSyAfaYz3fgaT4GA2rLb_iF3nbpUoo8-e1Ss'
    base_url = 'https://maps.googleapis.com/maps/api/distancematrix/json?'

    # parse each location 
    location_request = ''
    for loc in locations:
        location_request = location_request + '|%s,%s' % (loc[0],loc[1])

    # specify origins
    origin_request = 'origins='
    if origin: 
        origin_request = origin_request + '%s,%s' % (origin[0],origin[1])
        origin_request = origin_request + location_request
    else:
        origin_request = origin_request + location_request[1:]

    # specify destinations
    destination_request = '&destinations='
    destination_request = destination_request + location_request[1:]

    mode_request = '&mode=' + mode
    api_request = '&key=' + google_api_key
    complete_url = base_url + origin_request + destination_request + mode_request + api_request 

    googleResponse = urllib.urlopen(complete_url)
    jsonResponse = json.loads(googleResponse.read())

    #pprint.pprint(jsonResponse)    
    return jsonResponse

# format query and look up using google geocoding API when elements exceed 10 
def get_google_direction_matrix_extended(all_locations,origin=None,pairwise=True,mode='walking'):
    import time

    google_api_key = 'AIzaSyAfaYz3fgaT4GA2rLb_iF3nbpUoo8-e1Ss'
    #google_api_key = 'AIzaSyDL3SBSFF2bwdvRjr6NaTW6iUH5Dwr53_g'
    base_url = 'https://maps.googleapis.com/maps/api/distancematrix/json?'

    distance_matrix = np.array([])
    duration_matrix = np.array([])
    max_items = len(all_locations)
    mode_request = '&mode=' + mode
    api_request = '&key=' + google_api_key

    if origin: 
        start = -1
    else:
        start = 0

    if pairwise:
        finish = max_items
    else:
        finish = 0

    querynum = 90

    # do one origin point at a time 
    for origidx in range(start, finish):
        # specify origin 
        print origidx
        if origidx == -1:
            origin_request = 'origins=%s,%s' % (origin[0],origin[1])
        else:
            origin_loc = all_locations[origidx]
            origin_request = 'origins=%s,%s' % (origin_loc[0],origin_loc[1])
        
        # specify destination 10 at a time and query 
        distance_dest = np.array([])
        duration_dest = np.array([])
        time.sleep(0.5)

        # request each destination 
        for init_item in range( (max_items-1) / querynum + 1):
            
            # do 10 at a time 
            if init_item < max_items / querynum:
                item_idx = [x + init_item*querynum for x in range(querynum)]
            else:
                item_idx = [x + init_item*querynum for x in range(0, max_items%querynum)]
            locations = [all_locations[i] for i in item_idx]

            # parse each location 
            location_request = ''
            for loc in locations:
                location_request = location_request + '|%s,%s' % (loc[0],loc[1])

            # specify destinations
            destination_request = '&destinations='
            destination_request = destination_request + location_request[1:]

            complete_url = base_url + origin_request + destination_request + mode_request + api_request 

            # request from google 
            googleResponse = urllib.urlopen(complete_url)
            jsonResponse = json.loads(googleResponse.read())

            # convert into numpy array 
            rows = jsonResponse['rows']
            distance_row,duration_row = get_distance_matrix(rows)

            # extend row
            distance_dest = np.append(distance_dest, distance_row[0])
            duration_dest = np.append(duration_dest, duration_row[0])

        if distance_matrix.size>0:
            distance_matrix = np.vstack([distance_matrix, distance_dest])
            duration_matrix = np.vstack([duration_matrix, duration_dest])
        else:
            distance_matrix = distance_dest
            duration_matrix = duration_dest

    return distance_matrix, duration_matrix


def get_distance_matrix(rows):
    # t0 = time.time()
    distance_value = []
    duration_value = []
    for row in rows:
        #dist_col_km = []
        dist_col_val = []
        #dur_col_min = []
        dur_col_val = []
        for col in row['elements']:
            if col['status'] == 'OK':
                dist = col['distance']
                #dist_col_km.append(float(dist['text'].encode('ascii').rstrip(' km')))
                dist_col_val.append(dist['value']) # meters 
                dur = col['duration']
                #dur_col_min.append(float(dur['text'].encode('ascii').rstrip(' mins')))
                dur_col_val.append(dur['value']) # seconds 
            else:
                print col['status']
                dist = 1000000000
                dur = 1000000000
                dist_col_val.append(dist)
                dur_col_val.append(dur)

        distance_value.append(dist_col_val)
        duration_value.append(dur_col_val)
    # convert into numpy matrices
    distance_value = np.asarray(distance_value)
    duration_value = np.asarray(duration_value)
    return (distance_value,duration_value)

if __name__ == '__main__':
    import time 
    from flickr_sites import get_centroids_timescore_sql
    from matplotlib import pyplot as plt
    con = mdb.connect('localhost', 'root', '', 'insight')

    # test the get_google_address function by looking up addresses in tripomatic database
    def test1():
        with con:
            cur = con.cursor(mdb.cursors.DictCursor)
            cur.execute("SELECT Id, Name, Address FROM tripomatic")
            rows = cur.fetchall()
            for row in rows:
                print '\n====================================='
                print row["Id"], row["Name"]
                print row["Address"]
                if row["Address"]:
                    lookupVal = row["Address"]
                else:
                    lookupVal = row['Name']
                    print 'Look up by Name!!!'
                if lookupVal:
                    results = get_google_address(lookupVal)
                    for result in results:
                        print '----------------------------------'
                        #print.pprint(result['geometry']['location'])
                        pprint.pprint(result['geometry'])
                        pdb.set_trace()

    # test google direction matrix API
    def test2():
        # get a bunch of locations from sql
        init_loc = [40.74844,-73.985664]
        centroids = get_centroids_timescore_sql(con,init_loc,9)
        nearby_locs = [[cent['lat'],cent['lng']] for cent in centroids] 

        # try querying google api 
        t0 = time.time()
        jsonResponse = get_google_direction_matrix(nearby_locs,init_loc)
        rows = jsonResponse['rows']
        distance_matrix,duration_matrix = get_distance_matrix(rows)
        print 'querying and building distance matrix for %s nearby locations: %s s' % (len(nearby_locs), time.time()-t0)
        print distance_matrix
        # image 
        plt.imshow(distance_matrix, interpolation='nearest')
        #plt.imshow(duration_matrix, interpolation='nearest')
        plt.show()


    def test3():
        import pickle
        import pandas as pd
        # get a bunch of locations from sql
        #init_loc = [40.74844,-73.985664]
        #centroids = get_centroids_timescore_sql(con,init_loc,10)
        
        with con:
            cur = con.cursor(mdb.cursors.DictCursor)
            cmd = "SELECT * FROM flickr_clusters_nyc2"
            cur.execute(cmd)
            centroids = cur.fetchall()

        nearby_locs = [[cent['lat'],cent['lng']] for cent in centroids]
        distance_matrix, duration_matrix = get_google_direction_matrix_extended(nearby_locs)
        
        # pickle these 
        #pickle.dump( distance_matrix, open( "distance_matrix.p", "wb" ) )
        #pickle.dump( duration_matrix, open( "duration_matrix.p", "wb" ) )
        #distance_matrix = pickle.load( open( "distance_matrix.p", "rb" ) )
        plt.imshow(distance_matrix, interpolation='nearest')
        plt.show()

        distance_matrix = pd.DataFrame(distance_matrix)
        duration_matrix = pd.DataFrame(duration_matrix)

        distance_matrix.to_sql(name='flickr_clusters_nyc2_distmat',con=con,flavor='mysql',if_exists='replace')
        duration_matrix.to_sql(name='flickr_clusters_nyc2_durmat', con=con,flavor='mysql',if_exists='replace')
        print 'matrices saved!'

    def test3b():
        init_loc = [40.74844,-73.985664]
        centroids = get_centroids_timescore_sql(con,init_loc,10)
        nearby_locs = [[cent['lat'],cent['lng']] for cent in centroids]
        distance_matrix, duration_matrix = get_google_direction_matrix_extended(nearby_locs,origin=init_loc,pairwise=False)
        print distance_matrix, duration_matrix


    def test3_save():
        import pickle
        import pandas as pd
        distance_matrix = pickle.load( open( "distance_matrix.p", "rb" ) )
        duration_matrix = pickle.load( open( "duration_matrix.p", "rb" ) )

        distance_matrix = pd.DataFrame(distance_matrix)
        duration_matrix = pd.DataFrame(duration_matrix)

        distance_matrix.to_sql(name='flickr_clusters_nyc2_distmat',con=con,flavor='mysql',if_exists='replace')
        duration_matrix.to_sql(name='flickr_clusters_nyc2_durmat', con=con,flavor='mysql',if_exists='replace')

    # test google direction matrix API integration with best path finder 
    def test4():
        from mypath import find_best_path
        # initial and all possible locations 
        init_loc = [40.74844,-73.985664]
        nearby_locs = [[ 40.75690913, -73.98618134], \
        [ 40.74845804, -73.98557143], [ 40.75274964, -73.97727833], [ 40.75061299, -73.99353062],\
        [ 40.75315722, -73.9821481 ], [ 40.7540401 , -73.98401502], [ 40.74050068, -73.98470645],\
        [ 40.7416182, -73.9893952], [ 40.7501 , -73.98791818]]
        # assumes one hour at each location 
        duration_at_each_location = np.ones(len(nearby_locs)+1)*3600
        # time score is obtained from flickr photo density 
        time_score = np.random.rand(len(nearby_locs)+1,48)
        
        # --------
        # First, query google directions API
        t0 = time.time()
        jsonResponse = get_google_direction_matrix(nearby_locs,init_loc)
        rows = jsonResponse['rows']
        distance_matrix,duration_matrix = get_distance_matrix(rows)
        print 'querying and building distance matrix', time.time()-t0

        # Then, find the best paths given direction matrix, time at each place, and time score
        t1 = time.time()
        nvisits = 5
        path, time_idx = find_best_path(distance_matrix,duration_matrix,nvisits,\
            loc_duration=duration_at_each_location,time_score=time_score)
        print path
        print 'visiting %d locations out of %d :' % (nvisits,len(nearby_locs)+1), time.time()-t1
        #pdb.set_trace()

    # test google places api --> reverse lookup 
    def test5():
        location = [40.74844,-73.985664]
        jsonResponse = get_google_places(location[0], location[1])
        for response in jsonResponse:
            print response['name']

    test3()
