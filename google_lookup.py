import urllib, json
import pymysql as mdb
import pprint
import pdb
import numpy as np
from matplotlib import pyplot as plt
from mypath import find_best_path
#%reload_ext autoreload

# TODO: add walking versus biking mode

# format query and look up using google geocoding API
def get_google_address(address):
    google_api_key = 'AIzaSyAfaYz3fgaT4GA2rLb_iF3nbpUoo8-e1Ss'
    address_formatted = '+'.join(address.split(' '))
    base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    address_request = 'address=' + address_formatted
    api_request = '&key=' + google_api_key
    complete_url = base_url + address_request + api_request 

    googleResponse = urllib.urlopen(complete_url)
    jsonResponse = json.loads(googleResponse.read())
    if jsonResponse['status'] == 'OK':
        results = jsonResponse['results']
        if len(results) > 1:
            print 'Warning, more than one result returned!!!!'
            #pdb.set_trace()
            #pprint.pprint(results)
    else:
        print jsonResponse['status']
        results = None
    return results

# format query and look up using google geocoding API
def get_google_direction_matrix(locations,origin=None):
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

    mode_request = '&mode=walking'
    api_request = '&key=' + google_api_key
    complete_url = base_url + origin_request + destination_request + mode_request + api_request 

    googleResponse = urllib.urlopen(complete_url)
    jsonResponse = json.loads(googleResponse.read())

    #pprint.pprint(jsonResponse)    
    
    return jsonResponse


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
        distance_value.append(dist_col_val)
        duration_value.append(dur_col_val)
    # convert into numpy matrices
    distance_value = np.asarray(distance_value)
    duration_value = np.asarray(duration_value)
    #pdb.set_trace()
    # # image 
    # plt.imshow(distance_value, interpolation='nearest')
    # plt.imshow(duration_value, interpolation='nearest')
    # plt.show()
    # print time.time() - t0
    return (distance_value,duration_value)

if __name__ == '__main__':

    # test the get_google_address function by looking up addresses in tripomatic database
    def test1():
        con = mdb.connect('localhost', 'root', '', 'insight')
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

    def test2():
        import time 
        # test google direction matrix API
        init_loc = [40.74844,-73.985664]
        # nearby_locs = [[ 40.75690913, -73.98618134], \
        # [ 40.74845804, -73.98557143], [ 40.75274964, -73.97727833], [ 40.75061299, -73.99353062],\
        # [ 40.75315722, -73.9821481 ], [ 40.7540401 , -73.98401502], [ 40.74050068, -73.98470645],\
        # [ 40.7416182, -73.9893952], [ 40.7501 , -73.98791818]]
        nearby_locs = [[ 40.75690913, -73.98618134], \
        [ 40.74845804, -73.98557143], [ 40.75274964, -73.97727833], [ 40.75061299, -73.99353062],\
        [ 40.75315722, -73.9821481 ], [ 40.7540401 , -73.98401502], [ 40.74050068, -73.98470645],\
        [ 40.7416182, -73.9893952]]
        # assumes one hour at each location 
        duration_at_each_location = np.ones(len(nearby_locs))
        # time score is obtained from flickr photo density 
        time_score = np.random.rand(len(nearby_locs))

        # TODO: NEED TO DO SOMETHING WITH DURATION!!!!
        # Also: do something with initial location - right now assumes first point is initial point 
        jsonResponse = get_google_direction_matrix(nearby_locs,init_loc)
        rows = jsonResponse['rows']
        distance_matrix,duration_matrix = get_distance_matrix(rows)

        t0 = time.time()
        path = find_best_path(distance_matrix,duration_matrix,8,loc_duration=[1,1,1,1,1,1,1,1,1])
        print path
        print time.time()-t0
        #pdb.set_trace()

    test2()
