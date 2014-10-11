from flask import render_template, request
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

# landing page 
@app.route('/')
@app.route('/index')
def landing():
    return render_template('index.html')

@app.route('/slides')
def slides():
    return render_template('slides.html')

# map page 
@app.route('/map', methods=["POST"])
def map():
    print '------------------------------------'
    db = mdb.connect('localhost', 'root', '', 'insight')
    print request.form
    t1 = time.time()

    do_heatmap = True
    heatmap_db = 'flickr_yahoo_nyc2'
    if heatmap_db == 'flickr_yahoo_nyc2':
        cluster_min_samples = 200
    elif heatmap_db == 'flickr_yahoo_nyc':
        cluster_min_samples = 1000

    do_centroid  = 2  # 0 no, 1, compute online, 2 fetch from database 
    do_timescore = 1  # 1 = yes, 0 = no, 2 = constant 
    do_attractions = False
    do_path = True
    distance_matrix_method = 2 # 1 for live query, # 2 for loading from database
    maxlocs = 10
    maxdist = 1.5 / 69. # radius for maximal walking 
    init_time_hr = int(request.form['startingTime'])
    time_req = int(request.form['time_req'])
    pop_req = (int(request.form['pop_req']) - 1) / 4.
    # tailor number of visits per location 
    nvisits = time_req + 2 if time_req < 5 else 6
    print 'visiting %d places out of %d' % (nvisits, maxlocs)

    # initialize starting location from get request
    results = get_google_address(request.form['startingLocation'])
    if len(results) > 1:
        print 'Warning!!! %d locations found for starting address' % len(results)
    pprint.pprint([result['formatted_address'] for result in results])
    # set to the first one 
    init_loc = results[0]['geometry']['location'].values()
    init_address = results[0]['formatted_address'].rstrip(', USA')
    print 'initial location:', request.form['startingLocation'], init_loc
    
    if not within_nyc_bounds(init_loc[0],init_loc[1]):
        raise InvalidUsage("Starting location not found in New York")

    #------------------------------------------------------------------
    # get heatmap 
    #------------------------------------------------------------------
    try :
        t0 = time.time()
        if do_heatmap:
            heatmap = get_heatmap_sql2(db,init_loc,maxdist,which_table=heatmap_db, maxnum=40000)
        else:
            heatmap = []
        print time.time() - t0, "seconds wall time", len(heatmap), "heatmap values"

    except Exception as e:
        raise InvalidUsage('Uh-oh! Something went wrong')


    #------------------------------------------------------------------
    # cluster flickr photos to find centroids 
    #------------------------------------------------------------------
    t0 = time.time()
    if do_centroid == 1:
        centroids,labels = get_clusters_dbscan(heatmap,min_samples=cluster_min_samples)
        centroids_full = pd.DataFrame(centroids,columns=['lat','lng']) 

    elif do_centroid == 2:
        # find all the centroids within a certain distance 
        centroids_full = get_centroids_timescore_sql(db,init_loc,maxdist=maxdist,num=100)
        
        # throw an error if we end up with less than 3 
        if len(centroids_full) < 3:
            raise InvalidUsage("Not enough locations of interest found within walking distance")
        print '%s centroids found within %s mi' %(len(centroids_full), maxdist*69)

        centroids_full = pd.DataFrame(centroids_full)
        
        # sort by a weighted average of the two populations
        centroids_full['nycscore'] = (pop_req*centroids_full['nphotos_out'] + \
            (1-pop_req)*centroids_full['nphotos_nyc']) / centroids_full['nphotos']
        
        # sort -- use mergesort for stability
        centroids_full = centroids_full.sort('nycscore',ascending=False, kind='mergesort')
        # restrict to the top maxlocs entries 
        if centroids_full.shape[0] > maxlocs:
            centroids_full = centroids_full.head(maxlocs)       
            #centroids_full = centroids_full.reset_index()

        # # if to few locations to choose from 
        # if centroids_full.shape[0] < 5:
        #     print 'redoing clustering online!!'
        #     centroids,labels = get_clusters_dbscan(heatmap,min_samples=cluster_min_samples-80)
        #     centroids_full = pd.DataFrame(centroids,columns=['lat','lng'])
        #     if centroids_full.shape[0] > maxlocs:
        #         centroids_full['dist'] = (centroids_full['lat']-init_loc[0])**2 + (centroids_full['lng']-init_loc[1])**2
        #         centroids_full = centroids_full.sort('dist',kind='mergesort')
        #         centroids_full = centroids_full.head(maxlocs)
        #         centroids = centroids_full[['lat','lng']].values
        # else:

        # set centroid index to index 
        centroids_full = centroids_full.set_index(['index'])
        centroids = centroids_full[['lat','lng']].values
        # can only visit up to the number of candidate locations available within this distance
        if nvisits > centroids_full.shape[0]:
            nvisits = centroids_full.shape[0]
            print 'warning!!! not enough candidate locations near initial location!'

    else:
        centroids = []
        centroids_full = pd.DataFrame([])
    #print centroids
    print time.time() - t0, "seconds for %d centroids" % len(centroids)


    #-------------------------------------------------------------------------------
    # get score(time) for each centroid - load from database rather than calculate online
    #-------------------------------------------------------------------------------
    # time score = [nlocations x ntimepoints]
    try :
        t0 = time.time()
        hour_keys = [str(x) for x in  np.linspace(0,24,49)]
        hour_keys = hour_keys[:-1]
        if do_timescore == 1:
            # calculate time score !!
            #time_score = centroids_full[hour_keys].values
            # do a weighted average of the two time courses 
            # when the weight is 0.5, this should come out to similar to just getting get time score without dividing by user
            centroids_nyc = get_centroids_timescore_sql(db,init_loc,maxdist=maxdist,num=100, name='flickr_clusters_nyc2_nycusers') 
            centroids_nyc = pd.DataFrame(centroids_nyc)
            centroids_nyc = centroids_nyc.set_index('index').ix[centroids_full.index]

            centroids_out = get_centroids_timescore_sql(db,init_loc,maxdist=maxdist,num=100, name='flickr_clusters_nyc2_outusers') 
            centroids_out = pd.DataFrame(centroids_out)
            centroids_out = centroids_out.set_index('index').ix[centroids_full.index]

            time_score = (pop_req * centroids_out[hour_keys].values) + ((1 - pop_req) * centroids_nyc[hour_keys].values)
        else:
            time_score = np.ones((len(centroids),48))
            if do_timescore == 2:
                score = centroids_full[hour_keys].sum(axis=1)
                time_score = time_score * score[:,None]

        # add a row of zeros in the beginning, corresponding to the initial starting location
        # this should not count for anything 
        time_score = np.vstack([np.zeros(48), time_score])

        # photo_score_withtime = []
        # for cent in centroids:
        #     centroid_photos_withtime = get_timemap_sql(db,cent)
        #     hour_mean = get_photo_density(centroid_photos_withtime)
        #     photo_score_withtime.append(hour_mean)
        print time.time() - t0, "seconds for getting centroid scores with weight", pop_req
    
    except Exception as e:
        raise InvalidUsage('Uh-oh! Something went wrong obtaining time scores')


    #-------------------------------------------------------------------------------
    # calculate optimal path 
    #-------------------------------------------------------------------------------
    try :
        if do_path:
            # query google distance matrix api and build distance matrix
            t0 = time.time()
            if distance_matrix_method == 1:
                jsonResponse = get_google_direction_matrix(centroids,init_loc)
                rows = jsonResponse['rows']
                distance_matrix,duration_matrix = get_distance_matrix(rows)

            elif distance_matrix_method == 2: # or load from precomputed values saved in db
                # get the distance from starting location to all centroids 
                distance_matrix,duration_matrix = get_google_direction_matrix_extended(centroids,origin=init_loc,pairwise=False)
                # get all pairwise distance from database
                distance_matrix0, duration_matrix0 = get_distdur_matrix_sql(db, centroids_full.index.values)
                # append it together with distance matrices for initial location 
                distance_matrix = np.vstack([distance_matrix, distance_matrix0])
                duration_matrix = np.vstack([duration_matrix, duration_matrix0])

            print time.time() - t0, 'seconds for querying and building distance matrix'

            # find optimal path
            t0 = time.time()
            duration_at_each_location = get_estimated_duration_sql(db, centroids_full.index.values)
            duration_at_each_location = np.insert(duration_at_each_location,0,0)
            duration_at_each_location = duration_at_each_location * (2./time_req+0.5)
            print 'duration multiplier = %s' % (2./time_req+0.5), time.time()-t0

            path, path_time_idx = find_best_path(distance_matrix,duration_matrix,nvisits,\
                loc_duration=duration_at_each_location.tolist(),time_score=time_score,init_time_secs=init_time_hr*60*60)
            print time.time() - t0, 'seconds. best path found: ', path, path_time_idx
            pathlocs = []
            for p in path:
                pathlocs.append((p[1], centroids[p[1]]))
        else:
            # assumes one hour at each location, except the starting location 
            duration_at_each_location = np.ones(len(centroids))*3600
            pathlocs = []

        dur_transit = [duration_matrix[p] for p in path]
        #print '%d path locations: ' % len(pathlocs), pathlocs
    except Exception as e:
        raise InvalidUsage('Uh-oh! Something went wrong calculating the path')


    try :
        #-------------------------------------------------------------------------------
        # get the thumb nails of locations
        #-------------------------------------------------------------------------------
        t0 = time.time()
        thumb_urls = []
        #thumb_tags = []
        hour_idx = np.linspace(0,24,49)[:-1]
        for idx,p in enumerate(path):
            #thumb_urls.append(get_thumb_sql(db,centroids_full.index[p[1]], topnum=5))
            thumbs = get_thumb_byhour_sql2(db,centroids_full.index[p[1]], \
                int(hour_idx[path_time_idx[idx]]), topnum=4)
            thumb_urls.append(thumbs)
            #tags = []
            #for thumb in thumbs:
            #    tags.append([tag['tag'] for tag in get_thumb_tag_sql(db, thumb['Id'])])
            #thumb_tags.append(tags)
        print time.time() - t0, "seconds for photo thumbnails"

        #-------------------------------------------------------------------------------
        # get google places for each location 
        #-------------------------------------------------------------------------------
        t0 = time.time()
        googlePlaces = []
        for loc in pathlocs:
            places = get_google_places(loc[1][0], loc[1][1], radius=50)
            places_formated = []
            for pl in places[ : min(5,len(places)) ]: # save the top five
                if 'icon' not in pl: # add custom default icon if no icon from google maps
                    pl.update({'icon': 'static/img/map-marker-19.svg'})
                places_formated.append({'name': pl['name'], 'icon': pl['icon'], \
               'lat': pl['geometry']['location']['lat'], 'lng': pl['geometry']['location']['lng']})
            googlePlaces.append(places_formated)
        print time.time() - t0, 'seconds for reverse google places search'

        # define hour scores 
        #time_score_df = centroids_full[hour_keys].T
        time_score_df = pd.DataFrame(time_score[1:].T)
        time_score_df.index = hour_keys
        print time.time() - t1, 'seconds total'

    except Exception as e:
        raise InvalidUsage(e)

    user_init = {'start_time': init_time_hr, 'start_address': init_address}
    
    # close connection 
    if db: db.close()

    return render_template("map.html", heatmaploc=heatmap, init_loc=init_loc, user_init=user_init, \
        centroids=centroids_full, path_locations=pathlocs, path_time_idx=path_time_idx, \
        dur_transit=dur_transit, duration_at_each_location=duration_at_each_location[1:], thumb_urls=thumb_urls, \
        time_score=time_score_df, google_places=googlePlaces)


#  --------------------Error handling --------------------
class InvalidUsage(Exception):
    """Class for handling excpetions"""
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = error.to_dict()
    message = response.get('message', '')
    return render_template('error.html', message = message)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html', message = "Page Not Found (404).")

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', message = "An unexpected error has occurred (500).")


#  --------------------some helper functions --------------------

# check whether input is within bounds 
def within_nyc_bounds(lat, lng):
    return (40.60 <= lat <= 40.90) and (-74.20 <= lng <= -73.70)

# loads estimated location data from flickr 
def get_estimated_duration_sql(db,clusterId):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT * FROM flickr_clusters_nyc2_visitdur" 
        cur.execute(cmd)
        centroids = cur.fetchall()
    centroids = pd.DataFrame(centroids)
    # [centroids['Dur'][centroids['ClusterId']==d].values for d in clusterId]
    return centroids['Dur'][clusterId].values

# load pre-saved distance/duration matrix from sql 
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
