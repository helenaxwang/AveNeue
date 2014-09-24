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
def get_heatmap_sql(db,init_loc,lim=0.01):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT Id,lat,lng,user_id,date_taken FROM flickr_yahoo_nyc \
        WHERE ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
        (init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
        cur.execute(cmd)
        heatmap = cur.fetchall()
    return heatmap

def get_heatmap_sql2(db,init_loc,lim=0.01, which_table='flickr_yahoo_nyc2'):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT lat,lng FROM %s \
        WHERE ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
        (which_table, init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
        cur.execute(cmd)
        heatmap = cur.fetchall()
    return heatmap

# query the time stamp for init_loc by looking in mysql 
def get_timemap_sql(db,init_loc,lim=0.005):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT Id,date_taken FROM flickr_yahoo_nyc WHERE ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
        (init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
        cur.execute(cmd)
        timemap = cur.fetchall()
    return timemap

# get precomputed centroids of flicker photos from heatmaps from sql
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

def get_centroids_timescore_sql(db,init_loc,num=5):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT *, POWER(lat - (%s), 2) + POWER(lng - (%s), 2) AS dist \
        FROM flickr_clusters_nyc2 ORDER BY dist LIMIT %d" %(init_loc[0], init_loc[1], num)
        cur.execute(cmd)
        centroids = cur.fetchall()
    #centroids = list(centroids)
    return centroids

def get_photo_density(photos, interval=30, drop_duplicates=True, normalize=False):
    # convert to data frame 
    photo_df = pd.DataFrame(photos)
    # interval in nanoseconds 
    nsround = interval*60*1000000000 
    # use time as an index -- round to the nearest interval
    #photo_df.index = pd.to_datetime(photo_df['date_taken'])
    photo_df['date_taken'] = pd.DatetimeIndex(((photo_df.date_taken.astype(np.int64) // nsround + 1 ) * nsround))
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


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from flickr_sites import *
    import pdb

    # tests photo density as a function of time 
    init_loc = [40.74844,-73.985664]
    db = mdb.connect('localhost', 'root', '', 'insight')
    centroid_photos_withtime = get_timemap_sql(db,init_loc)
    fig = plt.figure()
    ax1 = fig.add_subplot(211)
    hour_mean = get_photo_density(centroid_photos_withtime)
    ax1.plot(hour_mean)
    ax2 = fig.add_subplot(212)
    hour_mean = get_photo_density(centroid_photos_withtime,True)
    ax2.plot(hour_mean)
    plt.show()

