import pymysql as mdb
import pdb
import numpy as np
import math

# get the locations of tourist attractions 
def get_tripomatic_sql(db,lat,lng,lim=0.005):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT * FROM tripomatic JOIN tripomatic_latlng \
               ON tripomatic.Id = tripomatic_latlng.Id \
               WHERE ((loc_lat BETWEEN %s AND %s) AND (loc_lng BETWEEN %s AND %s))" %\
               (lat-lim/2,lat+lim/2,lng-lim/2,lng+lim/2)
        #cur.execute("SELECT Id, Name, Address FROM tripomatic")
        cur.execute(cmd)
        attractions = cur.fetchall()
    return attractions

# get the locations of tourist attractions by their bounding boxes 
# not used!! because bounding boxes are inacurate -- perhaps to be refined later 
def get_tripomatic_lookup_by_bounds(db,lat,lng):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT tripomatic.Id,loc_lat,loc_lng, viewport_sw_lat, viewport_sw_lng, viewport_ne_lat, viewport_ne_lng,\
        bounds_sw_lat, bounds_sw_lng, bounds_ne_lat, bounds_ne_lng, Name, Address \
        FROM tripomatic_latlng JOIN tripomatic \
        ON tripomatic_latlng.Id = tripomatic.Id \
        WHERE (viewport_sw_lat < %s AND %s < viewport_ne_lat) AND \
        (viewport_sw_lng < %s AND %s < viewport_ne_lng)" % (lat,lat,lng,lng)
        cur.execute(cmd)
        attractions = cur.fetchall()
    return attractions

# gaussian weighting function for approximity to tourist location 
def _gauss2(X, r0=(0,0), sigma=1):
    rad_sq = _dist_squared(X,r0)
    return math.exp(-(rad_sq)/(2*sigma**2))

def _dist_squared(x,y):
    return np.sum(np.square(np.array(x)-np.array(y)))

# TODO: need to get rid of duplicate locations! take their average!!! 
def touristy_score(location, attractions):
    dist_weight = [ 1./(att['Id']+1) * _gauss2( (att['loc_lat'], att['loc_lng']),  location, sigma=0.15/69) \
    for att in attractions]
    return 100*np.sum(dist_weight)