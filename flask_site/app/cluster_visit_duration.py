import pandas as pd 
import numpy as np

def cluster_duration(df, curr_loc, idx, min_hrdiff=0, max_hrdiff=480):
    # everything in the location 
    smallset  = df.ix[idx]
    # everything outside of the location 
    smallset2 = df.ix[idx == False]
    # find the earliest time inside the area and outside
    # grouped by date and user_id 
    inside_area_group  = smallset['date_taken'].groupby((lambda x: x.date(), smallset['user_id']))
    inside_area_first  = inside_area_group.first()
    inside_area_last   = inside_area_group.last()
    #outside_area = smallset2['date_taken'].groupby((lambda x: x.date(), smallset2['user_id'])).first()
    inside_area_first.name = 'inside_start'
    inside_area_last.name  = 'inside_end'
    #outside_area.name = 'outside_start'
    inside_area_first = inside_area_first.reset_index()
    inside_area_last  = inside_area_last.reset_index()
    #outside_area = outside_area.reset_index()
    # inner join to find that users that visit both inside and outside the area on the same day 
    combined = pd.merge(inside_area_first, inside_area_last, how='inner', on=['level_0', 'user_id'])
    # get the time difference
    timediff = combined['inside_end']-combined['inside_start']
    # return the median time bounded by some reasonable values, in seconds 
    return np.median(timediff[ (timediff>np.timedelta64(min_hrdiff, 'm')) \
        & (timediff<np.timedelta64(max_hrdiff, 'm')) ])/np.timedelta64(1, 's') 

def insert_centroids_visitdur_sql(con,idx,visitsec,init=True):
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS flickr_clusters_nyc2_visitdur")
            cur.execute("CREATE TABLE flickr_clusters_nyc2_visitdur(ClusterId Int PRIMARY KEY, Dur INT)")
        cmd = "INSERT INTO flickr_clusters_nyc2_visitdur (ClusterId, Dur) VALUES (%s, %s)" % (idx, visitsec)
        cur.execute(cmd)


if __name__ == '__main__':
    import pymysql as mdb
    from datetime import datetime
    import pdb
    dofull = True

    # get centroids from database 
    db = mdb.connect('localhost', 'root', '', 'insight')
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT * FROM flickr_clusters_nyc2")
        centroids = cur.fetchall()

    print 'loading photos from flickr_yahoo_nyc...'

    # import the full data set with redundancies and everything 
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT * FROM flickr_yahoo_nyc"
        cur.execute(cmd)
        photos = cur.fetchall()
    # convert into a data frame 
    photos2= pd.DataFrame(photos)
    # set index to datetime
    photos2.index = pd.to_datetime(photos2['date_taken'])
    
    print photos2.head()

    if dofull:
        #TODO: use the cluster labels to figure out photo affiliation, rather than restrict by radius
        radius = 0.005
        init = True
        for cent in centroids:
            curr_loc = (cent['lat'], cent['lng'])
            idx = (photos2['Lat']-curr_loc[0])**2 + (photos2['Lng']-curr_loc[1])**2 < radius ** 2
            duration = cluster_duration(photos2, curr_loc, idx, min_hrdiff=10, max_hrdiff=10*60)
            print cent['index'], curr_loc
            print '\t estimated visit duration: %s hr' % (duration/3600.)
            insert_centroids_visitdur_sql(db, cent['index'], duration, init)
            init = False

    else: # test one point to see that the conversion works  
        curr_loc = [40.74844,-73.985664]
        radius = 0.005
        idx = (photos2['Lat']-curr_loc[0])**2 + (photos2['Lng']-curr_loc[1])**2 < radius ** 2
        duration = cluster_duration(photos2, curr_loc, idx)
        print 'estimated visit duration: %s hr' % duration/3600. 

