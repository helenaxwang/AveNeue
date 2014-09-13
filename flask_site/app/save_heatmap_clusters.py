import pymysql as mdb
import pprint
import time 
import pdb
from flickr_sites import *


if __name__ == '__main__':
    con = mdb.connect('localhost', 'root', '', 'insight')

    # # empire state building, latitude/longitude
    init_loc = [40.74844,-73.985664] 
    lim = 0.5
    t0 = time.time()
    heatmap = get_heatmap_sql(con,init_loc,lim)
    #heatmap = []
    t1 = time.time() - t0
    print t1, "seconds wall time", len(heatmap), "values"

    centroids = get_clusters_dbscan(heatmap)
    
    init = True
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS flickr_clusters_nyc")
            cur.execute("CREATE TABLE flickr_clusters_nyc(ClusterId Int PRIMARY KEY AUTO_INCREMENT, Lat FLOAT, Lng FLOAT)")
        for cent in centroids:
            cmd = "INSERT INTO flickr_clusters_nyc (Lat, Lng) VALUES (%s, %s)" % (cent[0], cent[1])
            #pdb.set_trace()
            cur.execute(cmd)

