import pymysql as mdb
import pandas as pd

# inserts per hour score, plus longitutde and latitude 
def insert_centroids_sql_df(con,df,init=True):
    if init:
        if_exists = 'replace'
    else:
        if_exists = 'append'
    df.to_sql(name='flickr_clusters_nyc2',con=con,flavor='mysql',if_exists=if_exists)


def insert_centroids_sql(con,centroids,init=True):
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS flickr_clusters_nyc")
            cur.execute("CREATE TABLE flickr_clusters_nyc(ClusterId Int PRIMARY KEY AUTO_INCREMENT, Lat FLOAT, Lng FLOAT)")
        for cent in centroids:
            cmd = "INSERT INTO flickr_clusters_nyc (Lat, Lng) VALUES (%s, %s)" % (cent[0], cent[1])
            #pdb.set_trace()
            cur.execute(cmd)


if __name__ == '__main__':
    import time
    from flickr_sites import * 
    import pdb
    import matplotlib.pyplot as plt

    db = mdb.connect('localhost', 'root', '', 'insight')

    # # empire state building, latitude/longitude
    init_loc = [40.74844,-73.985664] 
    lim = 0.5

    # get a bunch of flicker photos from data base
    t0 = time.time()
    heatmap = get_heatmap_sql(db,init_loc,lim)
    #heatmap = []
    t1 = time.time() - t0
    print t1, "seconds wall time", len(heatmap), "values"

    # cluster them 
    t0 = time.time()
    centroids,labels = get_clusters_dbscan(heatmap)
    print time.time() - t0, "seconds wall time for clustering %d centroids" % len(centroids)
    
    t0 = time.time()
    # for each centroid of the cluster, compute time values
    hour_mean_list = []
    for cent in centroids:
        # get photos 
        centroid_photos_withtime = get_timemap_sql(db,cent)
        # get photo time line
        hour_mean = get_photo_density(centroid_photos_withtime)
        # add to this list 
        hour_mean_list.append(hour_mean)
    print time.time() - t0, "seconds wall time for computing hour scores"

    # convert into data frame 
    hour_means = pd.DataFrame(hour_mean_list)
    hour_means.index = range(len(centroids))
    temp = pd.DataFrame(centroids)
    hour_means['lat'] = temp[0]
    hour_means['lng'] = temp[1]
    #insert_centroids_sql(db,centroids,init=True)
    insert_centroids_sql_df(db,hour_means)
    


