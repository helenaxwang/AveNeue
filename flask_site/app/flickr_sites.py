import pandas as pd
import numpy as np
import pymysql as mdb
from datetime import datetime
#import matplotlib.pyplot as plt
#import json
import pdb

def get_clusters_kmeans(photos):
    from sklearn.cluster import KMeans

    photo_df = pd.DataFrame(photos)
    data = photo_df[['lat','lng']].values
    estimator = KMeans(init='k-means++', n_clusters=10, n_init=10)
    estimator.fit(data)
    centroids = estimator.cluster_centers_
    return centroids.tolist()


def get_clusters_dbscan(photos,eps=0.0005,min_samples=1000):
    from sklearn.cluster import DBSCAN

    photo_df = pd.DataFrame(photos)
    data = photo_df[['lat','lng']].values
    estimator = DBSCAN(eps=eps, min_samples=min_samples)
    estimator.fit(data)

    core_samples_mask = np.zeros_like(estimator.labels_, dtype=bool)
    core_samples_mask[estimator.core_sample_indices_] = True
    labels = estimator.labels_
    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)

    unique_labels = set(labels)
    centroids = []
    for k in unique_labels:
        class_member_mask = (labels == k)
        xy = data[class_member_mask & core_samples_mask]
        if k != -1:
            centroids.append(xy.mean(axis=0))
    print 'Estimated number of clusters: %d' % n_clusters_
    return centroids,labels

# query flickr photos in mysql from around init_loc to generate a heat map on google maps 
def get_heatmap_sql(db,init_loc,lim=0.01,user_name_exclude='atlanticyardswebcam04'):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT Id,lat,lng,user_id,date_taken FROM flickr_yahoo_nyc \
        WHERE ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
        (init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
        cmd += " AND user_name != '%s'" % user_name_exclude
        cur.execute(cmd)
        heatmap = cur.fetchall()
    return heatmap

# probably redundant with the one above but group by radius, fewer entries, and select tables 
def get_heatmap_sql2(db,init_loc,lim=0.01, maxnum=20000, which_table='flickr_yahoo_nyc2'):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT lat,lng FROM %s \
        WHERE POWER(lat - (%s), 2) + POWER(lng - (%s), 2) < POWER(%s, 2)\
        ORDER BY POWER(lat - (%s), 2) + POWER(lng - (%s), 2) LIMIT %d" % \
        (which_table, init_loc[0], init_loc[1], lim, init_loc[0], init_loc[1], maxnum)
        cur.execute(cmd)
        heatmap = cur.fetchall()
    return heatmap

# query the time stamp for init_loc by looking in mysql 
# no longer used except in testing 
def get_timemap_sql(db,init_loc,lim=0.005):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT Id,user_id,date_taken FROM flickr_yahoo_nyc WHERE ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
        (init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
        cur.execute(cmd)
        timemap = cur.fetchall()
    return timemap

# get precomputed centroids of flicker photos from heatmaps from sql
# no longer used 
def get_centroids_sql(db,init_loc,lim=0.01):
    with db:
        cur = db.cursor()
        cmd = "SELECT lat,lng FROM flickr_clusters_nyc WHERE ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
        (init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
        cur.execute(cmd)
        centroids = cur.fetchall()
    centroids = list(centroids)
    return centroids

# get precomputed centroids of flicker photos and their time courses from heatmaps from sql
# def get_centroids_timescore_sql(db,init_loc,lim=0.01):
#     with db:
#         cur = db.cursor(mdb.cursors.DictCursor)
#         cmd = "SELECT * FROM flickr_clusters_nyc2 WHERE ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
#         (init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
#         cur.execute(cmd)
#         centroids = cur.fetchall()
#     centroids = list(centroids)
#     return centroids

# find the num closest clusters near init_loc 
def get_centroids_timescore_sql(db, init_loc, maxdist=0.02, num=20, name='flickr_clusters_nyc2'):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT *, POWER(lat - (%s), 2) + POWER(lng - (%s), 2) AS dist FROM %s \
        HAVING dist < POWER(%s, 2) ORDER BY dist LIMIT %d" % (init_loc[0], init_loc[1], name, maxdist, num)
        cur.execute(cmd)
        centroids = cur.fetchall()
    #centroids = list(centroids)
    return centroids

def get_photo_density(photo_df, interval=30, drop_duplicates=True, normalize=False):
    # convert to data frame 
    if not isinstance(photo_df,pd.DataFrame):
        photo_df = pd.DataFrame(photo_df)
    # interval in nanoseconds 
    nsround = interval*60*1000000000 
    # use time as an index -- round to the nearest interval
    #photo_df.index = pd.to_datetime(photo_df['date_taken'])
    photo_df['date_taken'] = pd.DatetimeIndex(((photo_df.date_taken.astype(np.int64) // nsround ) * nsround))
    photo_df.index = photo_df['date_taken']
    # drop duplicate users 
    if drop_duplicates:
        photo_df = photo_df.drop_duplicates(['user_id','date_taken'])
        print '%d photos found' % photo_df.shape[0]
    # get the mean for each interal 
    hour_mean = photo_df.Id.groupby(lambda x: (x.hour, x.minute)).count() 
    # normalize by group total 
    if normalize:
        hour_mean = hour_mean / float(photo_df.Id.count())
    return hour_mean, photo_df

# computes moving average using circular convolution 
def _movingaverage(interval, window_size):
    from scipy.ndimage import convolve
    window= np.ones(int(window_size))/float(window_size)
    return convolve(interval, window, mode='wrap')

# computes the time score 
def compute_photo_timescore(photo_df, overall_density=None,smooth=3):
    hour_loc, pf = get_photo_density(photo_df, drop_duplicates=False) 
    if overall_density is not None:
        hour_loc = hour_loc / overall_density
    if smooth:
        hour_loc = _movingaverage(hour_loc,3)
    return hour_loc


# no longer used -- get thumbnails for a given location 
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

# get thumbnail for a given location at a particular time 
def get_thumb_byhour_sql(db,clusterId,hour,topnum=10):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT ClusterId, Fav, url, page_url, HOUR(date_taken) AS hour, flickr_clusters_nyc2_thumb.Id AS Id \
              FROM flickr_clusters_nyc2_thumb LEFT JOIN flickr_favorites \
              ON flickr_clusters_nyc2_thumb.Id = flickr_favorites.Id \
              LEFT JOIN flickr_yahoo_nyc \
              ON flickr_clusters_nyc2_thumb.Id = flickr_yahoo_nyc.Id \
              LEFT JOIN flickr_nyc_thumb \
              ON flickr_clusters_nyc2_thumb.Id = flickr_nyc_thumb.id \
              WHERE (ClusterId = %s) AND (Fav > 0) AND has_thumb = 1 \
              AND HOUR(date_taken) IN (%s, %s, %s) \
              ORDER BY Fav DESC LIMIT %s" % (clusterId, (hour-1)%24, hour%24, (hour+1)%24, topnum)
        cur.execute(cmd)
        fav_urls = cur.fetchall()
    return fav_urls

# get thumbnail for a given location at a particular time -- uses the secondarily saved table
# so it takes less time. should be the same as the one above 
def get_thumb_byhour_sql2(db,clusterId,hour,topnum=10):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT Fav, url, page_url \
              FROM flickr_clusters_nyc2_thumb2 WHERE ClusterId=%d AND hour = %d \
              ORDER BY Fav DESC LIMIT %d" % (clusterId, hour, topnum)
        cur.execute(cmd)
        fav_urls = cur.fetchall()
    return fav_urls

def get_thumb_tag_sql(db, photo_id):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT tag FROM flickr_yahoo_nyc_tags WHERE Id = %s" % photo_id
        cur.execute(cmd)
        tags = cur.fetchall()
    return tags


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import pdb
    db = mdb.connect('localhost', 'root', '', 'insight')

    # tests photo density as a function of time 
    def test1():
        init_loc = [40.74844,-73.985664]
        centroid_photos_withtime = get_timemap_sql(db,init_loc)
        fig = plt.figure()
        ax1 = fig.add_subplot(211)
        hour_mean,df = get_photo_density(centroid_photos_withtime)
        ax1.plot(hour_mean)
        ax2 = fig.add_subplot(212)
        hour_mean,df = get_photo_density(centroid_photos_withtime,drop_duplicates=True)
        ax2.plot(hour_mean)
        plt.show()


    def test2():
        thumbs = get_thumb_byhour_sql(db,clusterId=0, hour= 10,topnum=4)
        print thumbs

    def test3():
        import pprint, time
        t0 = time.time()
        write_to_newtable = True
        
        # fetch the total number of clusters 
        with db:
            cur = db.cursor()
            cur.execute('SELECT MAX(ClusterId) FROM flickr_clusters_nyc2_thumb')
            maxCluster = cur.fetchall()[0][0]
        print 'total number of clusters ', maxCluster+1

        table_name = 'flickr_clusters_nyc2_thumb2' # define new table name 
        init = True # initialize for writing to sql 
        for clusterId in range(0,maxCluster+1): # for each cluster 
            for hour in range(24): # for each hour 
                # fetch thumb nails 
                thumbs = get_thumb_byhour_sql(db,clusterId=clusterId,hour=hour,topnum=10)
                pprint.pprint(thumbs)

                # write to new table
                if write_to_newtable: 
                    for thumb in thumbs:
                        with db:
                            cur = db.cursor()
                            if init:
                                cur.execute("DROP TABLE IF EXISTS " + table_name)
                                cur.execute("CREATE TABLE %s(Id VARCHAR(25), ClusterId INT, Fav INT, hour INT, \
                                    url VARCHAR(100), page_url VARCHAR(100))" % table_name)
                            cmd = "INSERT INTO %s (Id, ClusterId, Fav, hour, url, page_url) \
                            VALUES ('%s', %s, %s, %s, '%s', '%s') " \
                            % (table_name, thumb['Id'], thumb['ClusterId'], thumb['Fav'], hour, thumb['url'], thumb['page_url'])
                            #print cmd
                            cur.execute(cmd)
                        init = False
            
        print time.time()-t0
    
    def test3new():
        print get_thumb_byhour_sql2(db,clusterId=1,hour=1,topnum=5)

    test3()
