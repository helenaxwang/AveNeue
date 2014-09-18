from flask import render_template, request, jsonify
from app import app
import pymysql as mdb
import pprint, time, math
import pdb
from flickr_sites import *
from google_lookup import *
from tripomatic_lookup import get_tripomatic_sql
from mypath import find_best_path
import pandas as pd
import numpy as np

db = mdb.connect('localhost', 'root', '', 'insight')

# landing page 
@app.route('/')
@app.route('/index')
def landing():
    return render_template('index.html')

#@app.route('/map', methods=["POST"])
@app.route('/map')
def map():
    do_heatmap = True
    do_centroid = 1 # 0 no, 1, compute online, 2 fetch from data base 
    do_timescore = False
    do_path = False
    do_attractions = True

    # initialize starting location from get request
    # print request.form
    # results = get_google_address(request.form['startingLocation'])
    # if len(results) > 1:
    #     print 'Warning!!! more than one location found %d' % len(results)
    # init_loc = results[0]['geometry']['location'].values()
    # print 'initial location:', request.form['startingLocation'], init_loc

    init_loc = [40.74844,-73.985664] # empire state building, latitude/longitude
    #init_loc = [40.7298482,-73.9974519] # washington square park 
    #init_loc = [40.7148731,-73.9591367] # williamsburg
    #init_loc = [40.7324628,-73.9900081] # third ave
    bound_in_miles = 1
    bound_in_latlng = bound_in_miles/69.
    #bound_in_latlng = 0.015

    # get heatmap 
    t0 = time.time()
    if do_heatmap:
        heatmap = get_heatmap_sql2(db,init_loc,bound_in_latlng,which_table='flickr_yahoo_nyc2')
    else:
        heatmap = []
    print time.time() - t0, "seconds wall time", len(heatmap), "heatmap values"
    #pprint.pprint(heatmap)

    # cluster flickr photos to find centroids 
    t0 = time.time()
    if do_centroid == 1:
        centroids,labels = get_clusters_dbscan(heatmap,min_samples=200)
        centroids_full = pd.DataFrame(centroids,columns=['lat','lng']) 
    elif do_centroid == 2:
        centroids_full = get_centroids_timescore_sql(db,init_loc,bound_in_latlng)
        centroids_full = pd.DataFrame(centroids_full)
        centroids = centroids_full[['lat','lng']].values
    else:
        centroids = []
        centroids_full = pd.DataFrame([])
    #print centroids
    print time.time() - t0, "seconds for %d centroids" % len(centroids)
    #centroids = [[40.74844,-73.985664]]

    # get time score for each centroid - load from database rather than calculate online
    # TODO HERE -- different way to summarize density 
    t0 = time.time()
    if do_timescore:
        hour_keys = [str(x) for x in range(24)]
        centroids_full['score'] = centroids_full[hour_keys].sum(axis=1)

        # calculate time score !!
        time_score = centroids_full[hour_keys].values
        # add a row of zeros in the beginning, corresponding to the initial starting location
        # this should not count for anything 
        time_score = np.vstack([np.zeros(24), time_score])
    else:
        time_score = np.random.rand(len(centroids)+1,24)
        if centroids:
            centroids_full['score'] = np.ones(len(centroids))

    # photo_score_withtime = []
    # for cent in centroids:
    #     centroid_photos_withtime = get_timemap_sql(db,cent)
    #     hour_mean = get_photo_density(centroid_photos_withtime)
    #     photo_score_withtime.append(hour_mean)
    print time.time() - t0, "seconds for getting centroid scores"
    #pdb.set_trace()

    # get the list of attractions within the vincinity
    t0 = time.time()
    if do_attractions:
        attractions = []
        for cent in centroids:
            attractions.extend(get_tripomatic_sql(db,cent[0],cent[1]))
    else:
        attractions = []
    print time.time() - t0, "seconds for looking up %d nearby attractions" % len(attractions)
    # print nearby attractions
    # ranking/id, name, distance(in miles) to starting location
    #pprint.pprint([(att['Id'], att['Name'], \
    #    69*np.sqrt(_dist_squared( (att['loc_lat'], att['loc_lng']),  init_loc )) ) for att in attractions])

    # proximity to attractions weighted by a gaussian 
    #dist_weight = [ ( 1./att['Id'], _gauss2( (att['loc_lat'], att['loc_lng']),  init_loc, sigma=0.15/69) ) \
    #for att in attractions]

    # calculate the touristiness of each location based proximity to nearby attractions
    # TODO: need to be normalized by flickr photo density 
    centroid_touristy_score = []
    for cent in centroids:
        centroid_touristy_score.append(touristy_score(cent, attractions))
    centroids_full['score'] = centroid_touristy_score

    # calculate optimal path 
    if do_path:
        maxlocs = 9
        nvisits = 5
        # query google distance matrix api and build distance matrix
        t0 = time.time()
        if len(centroids) > maxlocs:
            centroids = centroids[:maxlocs]
        jsonResponse = get_google_direction_matrix(centroids,init_loc)
        rows = jsonResponse['rows']
        distance_matrix,duration_matrix = get_distance_matrix(rows)
        print time.time() - t0, 'seconds for querying and building distance matrix'

        # find optimal path
        # assumes one hour at each location 
        duration_at_each_location = np.ones(len(centroids)+1)*3600
        path = find_best_path(distance_matrix,duration_matrix,nvisits,\
            loc_duration=duration_at_each_location,time_score=time_score)
        print 'best path found: ', path 
        #pdb.set_trace()
        pathlocs = [ init_loc ]
        for p in path:
            pathlocs.append(centroids[p[1]])
    else:
        pathlocs = []
    print 'path locations: ', pathlocs

    #pdb.set_trace()
    # box = [init_loc_dict['viewport']['southwest']['lat'], init_loc_dict['viewport']['southwest']['lng'],\
    #        init_loc_dict['viewport']['northeast']['lat'], init_loc_dict['viewport']['northeast']['lng']]
    return render_template("map_basic.html", heatmaploc=heatmap, myloc=init_loc,\
        centroids=centroids_full, attractions=attractions, path_locations=pathlocs)


# ----------------------------------------------------------------
# gaussian weighting function for approximity to tourist location 
def _gauss2(X, r0=(0,0), sigma=1):
    rad_sq = _dist_squared(X,r0)
    return math.exp(-(rad_sq)/(2*sigma**2))

def _dist_squared(x,y):
    return np.sum(np.square(np.array(x)-np.array(y)))

# TODO: need to get rid of duplicate locations! take their average!!! 
def touristy_score(location, attractions):
    dist_weight = [ 1./att['Id'] * _gauss2( (att['loc_lat'], att['loc_lng']),  location, sigma=0.15/69) \
    for att in attractions]
    return 100*sum(dist_weight)