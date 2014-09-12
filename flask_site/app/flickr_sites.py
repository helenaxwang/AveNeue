import pandas as pd
import numpy as np
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
    return centroids