from flask import render_template
from app import app
import pymysql as mdb
import pprint
import time 
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
def map_with_bootstrap():
    return render_template('index.html')

@app.route('/map')
def map():
    do_heatmap = False
    do_centroid = 2 # 0 no, 1, compute online, 2 fetch from data base 
    do_path = True
    do_attractions = False

    # get the attractions list 
    # attractions = get_tripomatic_sql()
    # this_attraction = attractions[43]
    # results = get_google_address(this_attraction['Address'])

    # initialize starting location 
    #init_loc = [40.74844,-73.985664] # empire state building, latitude/longitude
    init_loc = [40.7298482,-73.9974519] # washington square park 
    bound_in_miles = 1.0
    bound_in_latlng = bound_in_miles/69.
    #bound_in_latlng = 0.015

    # get heatmap 
    t0 = time.time()
    if do_heatmap:
        heatmap = get_heatmap_sql(db,init_loc,bound_in_latlng)
    else:
        heatmap = []
    print time.time() - t0, "Heatmap: seconds wall time", len(heatmap), "values"
    #pprint.pprint(heatmap)

    # calculate centroid of flickr photos
    t0 = time.time()
    if do_centroid == 1:
        centroids = get_clusters_dbscan(heatmap)
    elif do_centroid == 2:
        centroids_full = get_centroids_timescore_sql(db,init_loc,bound_in_latlng)
        centroids_full = pd.DataFrame(centroids_full)
        centroids = centroids_full[['lat','lng']].values
    else:
        centroids = []
    #print centroids
    print time.time() - t0, "seconds for %d centroids" % len(centroids)
    #centroids = [[40.74844,-73.985664]]

    # calculate time score 
    t0 = time.time()
    hour_keys = [str(x) for x in range(24)]
    centroids_full['score'] = centroids_full[hour_keys].sum(axis=1)
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

    # calculate optimal path 
    if do_path:
        # query google distance matrix api and build distance matrix
        t0 = time.time()
        if len(centroids) > 9:
            centroids = centroids[:9]
        jsonResponse = get_google_direction_matrix(centroids,init_loc)
        rows = jsonResponse['rows']
        distance_matrix,duration_matrix = get_distance_matrix(rows)
        print time.time() - t0, 'seconds for querying and building distance matrix'

        # computing time score - TODO: place holder right now!!!
        time_score = np.random.rand(len(centroids)+1,24)

        # find optimal path
        nvisits = 5
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
    return render_template("map_basic.html", heatmaploc=heatmap,myloc=init_loc,\
        centroids=centroids_full, attractions=attractions, path_locations=pathlocs)


@app.route("/db_fancy")
def cities_page_fancy():
    with db:
        cur = db.cursor()
        cur.execute("SELECT Name, CountryCode, Population FROM City ORDER BY Population LIMIT 15;")
        query_results = cur.fetchall()
    cities = []
    for result in query_results:
        cities.append(dict(name=result[0], country=result[1], population=result[2]))
    return render_template('cities.html', cities=cities)
