from flask import render_template
from app import app
import pymysql as mdb
import pprint
import time 
import pdb
from flickr_sites import *
from flickr_time_score import *
from google_lookup import *
from tripomatic_lookup import get_tripomatic_sql

#db = mdb.connect(user="root", host="localhost", db="world_innodb", charset='utf8')
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

    # get the attractions list 
    # attractions = get_tripomatic_sql()
    # this_attraction = attractions[43]
    # results = get_google_address(this_attraction['Address'])

    # initialize starting location 
    init_loc = [40.74844,-73.985664] # empire state building, latitude/longitude
    bound_in_miles = 0.1
    bound_in_latlng = bound_in_miles/69.
    #bound_in_latlng = 0.015

    # get heatmap 
    t0 = time.time()
    if do_heatmap:
        heatmap = get_heatmap_sql(db,init_loc,bound_in_latlng)
    else:
        heatmap = []
    t1 = time.time() - t0
    print t1, "Heatmap: seconds wall time", len(heatmap), "values"
    #pprint.pprint(heatmap)

    # calculate centroid of flickr photos
    bound_in_miles = 1
    bound_in_latlng = bound_in_miles/69.  
    if do_centroid == 1:
        centroids = get_clusters_dbscan(heatmap)
    elif do_centroid == 2:
        centroids = get_centroids_sql(db,init_loc,bound_in_latlng)
    else:
        centroids = []
    #print centroids
    #centroids = []
    print time.time() - t0, "seconds for centroid computation"
    #centroids = [[40.74844,-73.985664]]

    centroids_small = [init_loc]
    centroids_small.extend(centroids[1:2])
    print centroids_small
    # find the optimal path 
    jsonResponse = get_google_direction_matrix(centroids_small)
    rows = jsonResponse['rows']
    distance_matrix,duration_matrix = get_distance_matrix(rows)
    path = find_best_path(distance_matrix,duration_matrix)
    
    pathlocs = [ centroids_small[path[0][0]] ]
    for p in path:
        pathlocs.append(centroids_small[p[0]])

    # if centroids:
    #     for cent in centroids:
    #         centroid_photos_withtime = get_timemap_sql(db,init_loc)
    #         density_withtime = get_photo_density(centroid_photos_withtime)
    #         print time.time() - t0, "seconds for getting photo density"
    #         pdb.set_trace()

    # get the list of attractions within the vincinity == TO DO LATER
    #attractions = get_tripomatic_sql(db,centroids[0][0],centroids[0][1])
    #print time.time() - t0, "seconds for looking up nearby attractions"
    attractions = []
    #pdb.set_trace()
    # box = [init_loc_dict['viewport']['southwest']['lat'], init_loc_dict['viewport']['southwest']['lng'],\
    #        init_loc_dict['viewport']['northeast']['lat'], init_loc_dict['viewport']['northeast']['lng']]
    print pathlocs

    return render_template("map_basic.html", heatmaploc=heatmap,myloc=init_loc,\
        centroids=centroids, attractions=attractions, path_locations=pathlocs)


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
