from flask import render_template
from app import app
import pymysql as mdb
import pprint
import time 
import pdb
from flickr_sites import *
#from google_lookup import get_google_address
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
    
    # get the attractions list 
    # attractions = get_tripomatic_sql()
    # this_attraction = attractions[43]
    # results = get_google_address(this_attraction['Address'])

    # initialize starting location 
    init_loc = [40.74844,-73.985664] # empire state building, latitude/longitude
    lim = 0.01
    t0 = time.time()
    heatmap = get_heatmap_sql(init_loc,lim)
    #heatmap = []
    t1 = time.time() - t0
    print t1, "seconds wall time", len(heatmap), "values"
    
    # calculate centroid of attractions 
    #pprint.pprint(heatmap)
    centroids = get_clusters_dbscan(heatmap)
    #centroids = []
    print time.time() - t0, "seconds for centroid computation"
    #centroids = [[40.74844,-73.985664]]

    # get the list of attractions within the vincinity == TO DO LATER
    #attractions = get_tripomatic_sql(db,centroids[0][0],centroids[0][1])
    #print time.time() - t0, "seconds for looking up nearby attractions"
    attractions = []
    #pdb.set_trace()
    # box = [init_loc_dict['viewport']['southwest']['lat'], init_loc_dict['viewport']['southwest']['lng'],\
    #        init_loc_dict['viewport']['northeast']['lat'], init_loc_dict['viewport']['northeast']['lng']]

    return render_template("map_basic.html", heatmaploc=heatmap,myloc=init_loc,\
        centroids=centroids, attractions=attractions)


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


# ----------------------------------------------------------------------------------
# Helper functions 
# ----------------------------------------------------------------------------------
# get a heatmap of flickr photos 
def get_heatmap_sql(init_loc,lim=0.01):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT lat,lng FROM flickr_yahoo_nyc WHERE ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
        (init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
        cur.execute(cmd)
        heatmap = cur.fetchall()
    return heatmap