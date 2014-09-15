import pandas as pd
import numpy as np
import pymysql as mdb
from datetime import datetime
#import matplotlib.pyplot as plt
#import json
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN

def get_clusters_kmeans(photos):
    photo_df = pd.DataFrame(photos)
    data = photo_df[['lat','lng']].values
    estimator = KMeans(init='k-means++', n_clusters=10, n_init=10)
    estimator.fit(data)
    centroids = estimator.cluster_centers_
    return centroids.tolist()


def get_clusters_dbscan(photos):
    photo_df = pd.DataFrame(photos)
    data = photo_df[['lat','lng']].values
    estimator = DBSCAN(eps=0.0005, min_samples=1000)
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

# get a heatmap of flickr photos 
def get_heatmap_sql(db,init_loc,lim=0.01):
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT lat,lng FROM flickr_yahoo_nyc WHERE ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
        (init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
        cur.execute(cmd)
        heatmap = cur.fetchall()
    return heatmap

# get timeline of flickr photos 
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

def get_photo_density(photos,normalize=False):
    # convert to data frame 
    photo_df = pd.DataFrame(photos)
    # use time as an index
    #photo_df.index = pd.to_datetime(photo_df['date_taken'])
    photo_df.index  = photo_df['date_taken']
    # get hour mean 
    hour_mean = photo_df.Id.groupby(lambda x: x.hour).count() 
    # normalize by group total 
    if normalize:
        hour_mean = hour_mean / float(photo_df.Id.count())
    # normalize by total photos taken 
    hour_mean = hour_mean.astype('float64') / _get_total_photo_density(normalize)
    return hour_mean

## TODO: HAND CODE FOR NOW, need to save into data base 
def _get_total_photo_density(normalize=False):
    photos_by_hour = [25872, 15102, 11771,  9836,  9052,  8434,  9993, 14671, 22276,\
       26439, 34341, 43772, 54410, 57102, 56773, 57608, 56338, 50621,\
       48689, 49202, 42919, 38819, 32505, 25750]
    total_photos = 802295.0
    photo_density = np.array(photos_by_hour) 
    if normalize:
        photo_density = photo_density / total_photos
    return photo_density


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

