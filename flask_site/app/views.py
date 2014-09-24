from flask import render_template, request, jsonify
from app import app
import pymysql as mdb
import pprint, time, math
import pdb
from flickr_sites import *
from google_lookup import *
from tripomatic_lookup import *
from mypath import *
import pandas as pd
import numpy as np

db = mdb.connect('localhost', 'root', '', 'insight')

# landing page 
@app.route('/')
@app.route('/index')
def landing():
    return render_template('index.html')

# map page 
@app.route('/map', methods=["POST"])
#@app.route('/map')
def map():
    print request.form
    t1 = time.time()

    do_heatmap = False
    heatmap_db = 'flickr_yahoo_nyc2'
    if heatmap_db == 'flickr_yahoo_nyc2':
        cluster_min_samples = 200
    elif heatmap_db == 'flickr_yahoo_nyc':
        cluster_min_samples = 1000

    do_centroid  = 2 # 0 no, 1, compute online, 2 fetch from database 
    do_timescore = 1 # 1 = yes, 0 = no, 2 = constant 
    do_attractions = False
    location_score = 2 # 1 = touristiness, 2 = photo density 
    do_path = True
    distance_matrix_method = 2 # 1 for live query, # 2 for loading from database
    maxlocs = 10
    init_time_hr = int(request.form['startingTime'])
    time_req = int(request.form['time_req'])
    nvisits = time_req + 2; # tailor number of visits per location 
    print 'visiting %d places out of %d' % (nvisits, maxlocs)

    # initialize starting location from get request
    results = get_google_address(request.form['startingLocation'])
    if len(results) > 1:
        print 'Warning!!! more than one location found %d' % len(results)
    init_loc = results[0]['geometry']['location'].values()
    print 'initial location:', request.form['startingLocation'], init_loc

    #init_loc = [40.74844,-73.985664]    # empire state building, latitude/longitude
    #init_loc = [40.7298482,-73.9974519] # washington square park 
    #init_loc = [40.7148731,-73.9591367] # williamsburg
    #init_loc = [40.7324628,-73.9900081] # third ave
    #init_loc = [40.766117,-73.9786236]  # columbus circle 
    
    #------------------------------------------------------------------
    # get heatmap 
    #------------------------------------------------------------------
    t0 = time.time()
    if do_heatmap:
        bound_in_miles = 1.0
        bound_in_latlng = bound_in_miles/69. #0.015
        heatmap = get_heatmap_sql2(db,init_loc,bound_in_latlng,which_table=heatmap_db)
    else:
        heatmap = []
    print time.time() - t0, "seconds wall time", len(heatmap), "heatmap values"
    #pprint.pprint(heatmap)


    #------------------------------------------------------------------
    # cluster flickr photos to find centroids 
    #------------------------------------------------------------------
    t0 = time.time()
    if do_centroid == 1:
        centroids,labels = get_clusters_dbscan(heatmap,min_samples=cluster_min_samples)
        centroids_full = pd.DataFrame(centroids,columns=['lat','lng']) 
    elif do_centroid == 2:
        centroids_full = get_centroids_timescore_sql(db,init_loc,maxlocs) 
        centroids_full = pd.DataFrame(centroids_full)
        centroids = centroids_full[['lat','lng']].values
    else:
        centroids = []
        centroids_full = pd.DataFrame([])
    #print centroids
    print time.time() - t0, "seconds for %d centroids" % len(centroids)

    #----------------------------------------------------------------------------
    # get the list of attractions within the vincinity -- TODO: get all attractions at once?? get rid of redundancies??
    #----------------------------------------------------------------------------- 
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

    #------------------------------------------------------------------
    # calculate a score for each location -- mostly for display purposes?
    #------------------------------------------------------------------
    # the touristiness of each location based proximity to nearby attractions
    # TODO: need to be normalized by flickr photo density?
    if location_score == 1:
        centroid_touristy_score = []
        for cent in centroids:
            centroid_touristy_score.append(touristy_score(cent, attractions))
        centroids_full['score'] = centroid_touristy_score
    elif location_score == 2: # density of photos 
        centroids_full['score'] = centroids_full['nphotos']/1000.
    else: 
        centroids_full['score'] = np.ones(len(centroids))

    #-------------------------------------------------------------------------------
    # get score(time) for each centroid - load from database rather than calculate online
    #-------------------------------------------------------------------------------
    # TODO HERE -- different way to summarize density/interestingness??
    # time score = [nlocations x ntimepoints]
    t0 = time.time()
    if do_timescore == 1:
        #hour_keys = [str(x) for x in range(24)]
        #centroids_full['score'] = centroids_full[hour_keys].sum(axis=1)
        hour_keys = [str(x) for x in  np.linspace(0,24,49)]
        hour_keys = hour_keys[:-1]
        # calculate time score !!
        time_score = centroids_full[hour_keys].values
    else:
        time_score = np.ones((len(centroids),48))
        if do_timescore == 2:
            time_score = time_score * centroids_full['score'][:,None]
    # add a row of zeros in the beginning, corresponding to the initial starting location
    # this should not count for anything 
    time_score = np.vstack([np.zeros(48), time_score])

    # photo_score_withtime = []
    # for cent in centroids:
    #     centroid_photos_withtime = get_timemap_sql(db,cent)
    #     hour_mean = get_photo_density(centroid_photos_withtime)
    #     photo_score_withtime.append(hour_mean)
    print time.time() - t0, "seconds for getting centroid scores"
    #pdb.set_trace()

    #-------------------------------------------------------------------------------
    # calculate optimal path 
    #-------------------------------------------------------------------------------
    if do_path:
        # query google distance matrix api and build distance matrix
        t0 = time.time()
        if distance_matrix_method == 1:
            jsonResponse = get_google_direction_matrix(centroids,init_loc)
            rows = jsonResponse['rows']
            distance_matrix,duration_matrix = get_distance_matrix(rows)

        elif distance_matrix_method == 2:
            # get the distance from starting location to all centroids 
            distance_matrix,duration_matrix = get_google_direction_matrix_extended(centroids,origin=init_loc,pairwise=False)
            
            # get all pairwise distance from database
            distance_matrix0, duration_matrix0 = get_distdur_matrix_sql(db, centroids_full['index'].values)

            # append it together with distance matrices for initial location 
            distance_matrix = np.vstack([distance_matrix, distance_matrix0])
            duration_matrix = np.vstack([duration_matrix, duration_matrix0])

        print time.time() - t0, 'seconds for querying and building distance matrix'

        # find optimal path
        t0 = time.time()
        duration_at_each_location = get_estimated_duration_sql(db,centroids_full['index'].values)
        duration_at_each_location = np.insert(duration_at_each_location,0,0)
        duration_at_each_location = duration_at_each_location * (2./time_req+0.5)
        print 'duration multiplier = %s' % (2./time_req+0.5)

        path, path_time_idx = find_best_path_list(distance_matrix,duration_matrix,nvisits,\
            loc_duration=duration_at_each_location,time_score=time_score,init_time_secs=init_time_hr*60*60)
        print time.time() - t0, 'seconds. best path found: ', path
        pathlocs = []
        for p in path:
            pathlocs.append((p[1], centroids[p[1]]))
    else:
        # assumes one hour at each location, except the starting location 
        duration_at_each_location = np.ones(len(centroids))*3600
        pathlocs = []
    print '%d path locations: ' % len(pathlocs), pathlocs

    #-------------------------------------------------------------------------------
    # get the thumb nails of locations
    #-------------------------------------------------------------------------------
    # thumb_urls = []
    # for p in path:
    #     thumb_urls.append(get_thumb_sql(db,centroids_full['index'][p[1]], topnum=5))

    thumb_urls2 = []
    for cid in range(centroids_full.shape[0]):
        thumb_urls2.append(get_thumb_sql(db,centroids_full['index'][cid], topnum=4))

    #-------------------------------------------------------------------------------
    # get google places for each location 
    #-------------------------------------------------------------------------------
    t0 = time.time()
    googlePlaces = []
    for loc in pathlocs:
        places = get_google_places(loc[1][0], loc[1][1], radius=50)
        places_formated = []
        for pl in places[ : min(5,len(places)) ]: # save the top five
           places_formated.append({'name': pl['name'], 'icon': pl['icon'], \
           'lat': pl['geometry']['location']['lat'], 'lng': pl['geometry']['location']['lng']})
        googlePlaces.append(places_formated)
    print time.time() - t0, 'seconds for reverse google places search'
    #centroids_full = centroids_full.sort('score',ascending=False)

    # box = [init_loc_dict['viewport']['southwest']['lat'], init_loc_dict['viewport']['southwest']['lng'],\
    #        init_loc_dict['viewport']['northeast']['lat'], init_loc_dict['viewport']['northeast']['lng']]

    print time.time() - t1, 'seconds total'

    return render_template("map.html", heatmaploc=heatmap, myloc=init_loc,\
        centroids=centroids_full, attractions=attractions, path_locations=pathlocs, path_time_idx=path_time_idx, \
        duration_at_each_location=duration_at_each_location[1:], thumb_urls2=thumb_urls2, \
        time_score=centroids_full[hour_keys].T, google_places=googlePlaces)


def get_estimated_duration_sql(db,clusterId):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT * FROM flickr_clusters_nyc2_visitdur" 
        cur.execute(cmd)
        centroids = cur.fetchall()
    centroids = pd.DataFrame(centroids)
    # [centroids['Dur'][centroids['ClusterId']==d].values for d in clusterId]
    return centroids['Dur'][clusterId].values


def get_thumb_sql(db,clusterId,topnum=10):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT Fav, url FROM flickr_clusters_nyc2_thumb JOIN flickr_favorites \
              ON flickr_clusters_nyc2_thumb.Id = flickr_favorites.Id \
              WHERE (ClusterId = %s) AND (Fav > 0) ORDER BY Fav DESC LIMIT %s" % (clusterId, topnum)
        #print cmd
        cur.execute(cmd)
        fav_urls = cur.fetchall()
    return fav_urls

def get_distdur_matrix_sql(db, clusterId):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT * FROM flickr_clusters_nyc2_distmat")
        distance_matrix = cur.fetchall()
        cur.execute("SELECT * FROM flickr_clusters_nyc2_durmat")
        duration_matrix = cur.fetchall()
    # convert into data frames 
    distance_matrix = pd.DataFrame(distance_matrix)
    duration_matrix = pd.DataFrame(duration_matrix)
    # get matrices for current centroids 
    columns = [str(x) for x in clusterId]
    distance_matrix = distance_matrix.ix[clusterId][columns]
    duration_matrix = duration_matrix.ix[clusterId][columns]

    return distance_matrix, duration_matrix
