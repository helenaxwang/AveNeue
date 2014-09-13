
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json, os

# import everything into a list 
flickr_yahoo_path = 'flickr_yahoodata'
photos = []
for fnum in range(10):
    json_file_name = "yfcc100m_dataset-%d_nyc.json" % fnum
    print json_file_name
    with open(os.path.join(flickr_yahoo_path,json_file_name)) as fp:
        photos.extend(json.load(fp))

# convert into a data frame 
photo_df = pd.DataFrame(photos)

# limit data by a certain radius 
init_loc = (40.74844,-73.985664) # empire state building, latitude/longitude
radius = 0.01
idx = sqrt((photo_df['lng']-init_loc[1])**2 + (photo_df['lat']-init_loc[0])**2) < radius

# plot data 
plt.plot(photo_df['lng'][idx], photo_df['lat'][idx],'.k')

#from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN

data = photo_df[['lng','lat']][idx].values
#estimator = KMeans(init='k-means++', n_clusters=10, n_init=10)
#estimator.fit(data)
#centroids = estimator.cluster_centers_
#plt.scatter(centroids[:, 0], centroids[:, 1], marker='x', s=169, linewidths=2, color='r', zorder=10)
estimator = DBSCAN(eps=0.0005, min_samples=1000)
estimator.fit(data)

core_samples_mask = np.zeros_like(estimator.labels_, dtype=bool)
core_samples_mask[estimator.core_sample_indices_] = True
labels = estimator.labels_
n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)

# Black removed and is used for noise instead.
unique_labels = set(labels)
centroids = []
colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))
for k, col in zip(unique_labels, colors):
    if k == -1:
        # Black used for noise.
        col = 'k'

    class_member_mask = (labels == k)

    xy = data[class_member_mask & core_samples_mask]
    plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col,
             markeredgecolor='k', markersize=8)
    if k != -1:
        centroid = xy.mean(axis=0)
        centroids.append(centroid)
        plt.plot(centroid[0],centroid[1],'o',markersize=16)

    xy = data[class_member_mask & ~core_samples_mask]
    plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col,
             markeredgecolor='k', markersize=6)

plt.title('Estimated number of clusters: %d' % n_clusters_)
plt.show()

#------------------
db = mdb.connect('localhost', 'root', '', 'insight')
with db:
    cur = db.cursor(mdb.cursors.DictCursor)
    cmd = "SELECT * FROM tripomatic_latlng "
    cur.execute(cmd)
    attractions = cur.fetchall()
attractions = pd.DataFrame(attractions)

#------------------
# parse date time 
from datetime import datetime
#from dateutil.parser import parse

# check for date time convertable 
temp = pd.to_datetime(photo_df['date_taken'][0])
badidx = np.zeros(shape = (photo_df.shape[0]))
for idx,date in enumerate(photo_df['date_taken']):
    if type(pd.to_datetime(date)) != type(temp):
        print idx,date
        badidx[idx] = 1
# restrict data frame 
photos2 = photo_df.ix[badidx == 0]
# convert to date time and reset index
photos2.index = pd.to_datetime(photos2['date_taken'])
# get photos within reasonable window
photos2 = photos2.ix['2009':'2015'] #802295
#photos2 = photos2.set_index('date_taken')

# just work with the series
date_series = pd.Series(np.ones(photos2.shape[0]), index =photos2['date_taken'])
# group by hours 
#year_hour_means = date_series2.groupby(lambda x: (x.year, x.hour)).count()
#year_hour_means.index = pd.MultiIndex.from_tuples(year_hour_means.index, names=['year', 'hour'])
hour_means = date_series2.groupby(lambda x: x.hour).count()

# get the hour mean 
def get_hour_mean(photo_df, loc,radius=0.005,normalize=True):
    idx = np.sqrt((photo_df['lat']-loc[0])**2 + (photo_df['lng']-loc[1])**2) < radius
    hour_mean = photo_df.user_id[idx].groupby(lambda x: x.hour).count()
    if normalize:
        hour_mean = hour_mean / float(photo_df.user_id[idx].count())
    print sum(idx)
    return hour_mean

hour_all_normalized = photos2.user_id.groupby(lambda x: x.hour).count()/photos2.user_id.count()
hour_all = photos2.user_id.groupby(lambda x: x.hour).count()

# now findout hour means for different locations 
#init_loc1 = (40.74844,-73.985664) # empire state building, latitude/longitude
#init_loc1 = (40.752726,-73.977229) # Grand Central
init_loc1 = (40.7359464,-73.9889084) # union square
init_loc2 = (40.758895, -73.985131) # time square
init_loc3 = (40.7307465,-73.9976182) # washington square park 
init_loc4 = (40.7176379,-73.9599521) # williamsburg
init_loc5 = (40.7115551,-73.9531715) # mcdougal street 

allLocs = [init_loc1, init_loc2, init_loc3, init_loc4, init_loc5]
allLocNames = ['Union Square', 'Time Square', 'Washington Square Park', 'Williamsburg', 'McDougal Street']
#rcParams['figure.figsize'] = 6,4
fig = plt.figure(figsize=(6,4))
ax = fig.add_subplot(111)
colors = ['b','r','g','m','k']
locidx = range(0,4)#range(5,6)#range(3)
for i,loc in zip(locidx,allLocs[0:4]):
    #fig.suptitle(allLocNames[i], fontsize=14, fontweight='bold')
    hour_loc = get_hour_mean(photos2,loc,normalize=False)/hour_all
    plt.plot(xrange(24),hour_loc,colors[i],linewidth=2, label=allLocNames[i])
    plt.xlim([0,23])
    #plt.ylim([0,3])
    plt.xlabel('Hour',fontsize=12)
    plt.ylabel('Normalized photo density',fontsize=12)
    plt.legend(loc='best')
    #fig.set_size_inches(6,4)
    #plt.savefig('plots/empire.png',dpi=100)

