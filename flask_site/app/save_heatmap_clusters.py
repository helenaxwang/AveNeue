import pymysql as mdb
import pandas as pd

# resaves flickr data set (reduced after removing duplicates) along with cluster ids
def insert_flickr_sql_df(con,df,init=True,name='flickr_yahoo_nyc2'):
    if init:
        if_exists = 'replace'
    else:
        if_exists = 'append'
    df.to_sql(name=name,con=con,flavor='mysql',if_exists=if_exists)


# inserts per hour score, plus longitutde and latitude 
def insert_centroids_sql_df(con,df,init=True,name='flickr_clusters_nyc2'):
    if init:
        if_exists = 'replace'
    else:
        if_exists = 'append'
    df.to_sql(name=name,con=con,flavor='mysql',if_exists=if_exists)

# not used 
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


# Gets all the photos, clusters them into spatial clusters
# Figure out the time score for each cluster, and saves those into a new database
if __name__ == '__main__':
    import time
    from flickr_sites import * 
    import pdb
    import matplotlib.pyplot as plt
    import sys

    # run through small scale test 
    if len(sys.argv) > 1:
        fullrun = int(sys.argv[1])
    else:
        fullrun = 0
    print 'run full script ', fullrun
    
    if fullrun:
        lim = 0.5
    else:
        lim = 0.01

    # test here - adjust params 
    newtbname = 'flickr_clusters_nyc_test'
    interval = 10
    do_clustering = False
    do_save_new = True
    do_timescore_for_centroid = False
    save_timescore_for_centroid = False

    # connect to server 
    db = mdb.connect('localhost', 'root', '', 'insight')

    # empire state building, latitude/longitude
    init_loc = [40.74844,-73.985664] 
    
    # get a bunch of flicker photos from data base
    t0 = time.time()
    heatmap = get_heatmap_sql(db,init_loc,lim)
    #heatmap = []
    t1 = time.time() - t0
    print t1, "seconds wall time for", len(heatmap), "photos"

    # remove duplicates and get overall photo density
    hour_all, photo_df = get_photo_density(heatmap, interval=interval, drop_duplicates=True)
    print 'obtained %d entries of photos ' % photo_df.shape[0]
    # should have 253579 entries for photo_df

    if do_clustering:
        print 'running dbscan...'
        # cluster these photos into spatial clusters
        t0 = time.time()
        centroids,labels = get_clusters_dbscan(photo_df,min_samples=200)
        print time.time() - t0, "seconds wall time for clustering %d centroids" % len(centroids)
        # resave them into sql, with cluster labels
        photo_df['cluster_label'] = labels


    if do_save_new:
        print 'saving new flickr table...'
        # make a copy 
        photo_df2 = photo_df
        photo_df2 = photo_df2.set_index('Id')
        del photo_df2['date_taken'] # delete time because sql can't convert it well 
        insert_flickr_sql_df(db, photo_df2, name=newtbname)
        print 'saved new table: ' + newtbname


    if do_timescore_for_centroid:
        print 'computing hour scores...'
        t0 = time.time()
        # for each centroid of the cluster, compute time values
        hour_score_list = []
        hour_score_n = []
        cent_idx = range(len(centroids))
        for idx,cent in enumerate(centroids):
            try:
                # get photos near this centroid - TODO: use cluster information
                photo_idx = np.sqrt((photo_df['lat']-cent[0])**2 + (photo_df['lng']-cent[1])**2) < 0.005
                print 'number of photos near location ', sum(photo_idx)
                hour_score_n.append(sum(photo_idx))
                # normalize by time score 
                hour_score = compute_photo_timescore(photo_df.ix[photo_idx], hour_all, smooth=3)
                #centroid_photos_withtime = get_timemap_sql(db,cent)
                #hour_mean = get_photo_density(centroid_photos_withtime)
                # add to this list 
                hour_score_list.append(hour_score)
            except Exception as e:
                print e
                print idx, cent
                del cent_idx[idx]
        print time.time() - t0, "seconds wall time for computing hour scores"

        # convert into data frame 
        hour_means = pd.DataFrame(hour_score_list)
        # set index for the centroid numbers 
        #hour_means.index = range(len(centroids))
        hour_means.index = cent_idx
        
        # set the column names to the hour it is 
        time_axis = np.linspace(0,24,len(hour_all)+1)
        time_axis = time_axis[:-1]
        hour_means.columns = time_axis

        # add centroid lat and lng to it 
        temp = pd.DataFrame(centroids)
        hour_means['lat'] = temp[0][cent_idx]
        hour_means['lng'] = temp[1][cent_idx]

        # add the number of for photos for which it was computed
        hour_means['nphotos'] = hour_score_n

        # check for null values and fill them, otherwise can't input to sql 
        print 'number of nulls', [sum(hour_means[c].isnull()) for c in hour_means.columns]
        hour_means = hour_means.fillna(0)

    if save_timescore_for_centroid:
        #insert_centroids_sql(db,centroids,init=True)
        insert_centroids_sql_df(db,hour_means)
        print 'saved into flickr_clusters_nyc2 database'
    

