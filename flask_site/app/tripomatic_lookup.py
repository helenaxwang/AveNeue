import pymysql as mdb
import pdb

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
