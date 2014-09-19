import pandas as pd 
import numpy as np

def cluster_duration(df, curr_loc, idx, max_hrdiff=8):
    # everything in the location 
    smallset  = df.ix[idx]
    # everything outside of the location 
    smallset2 = df.ix[idx == False]
    # find the earliest time inside the area and outside
    # grouped by date and user_id 
    inside_area  = smallset['date_taken'].groupby((lambda x: x.date(), smallset['user_id'])).first()
    outside_area = smallset2['date_taken'].groupby((lambda x: x.date(), smallset2['user_id'])).first()
    inside_area.name = 'inside_start'
    outside_area.name = 'outside_start'
    inside_area = inside_area.reset_index()
    outside_area = outside_area.reset_index()
    # inner join to find that users that visit both inside and outside the area on the same day 
    combined = pd.merge(inside_area, outside_area, how='inner', on=['level_0', 'user_id'])
    # get the time difference
    timediff = combined['outside_start']-combined['inside_start']
    # return the median time bounded by some reasonable values, in seconds 
    return np.median(timediff[ (timediff>0) & (timediff<np.timedelta64(max_hrdiff, 'h')) ])/np.timedelta64(1, 's') 


if __name__ == '__main__':
    import pymysql as mdb
    from datetime import datetime

    print 'loading photos from flickr_yahoo_nyc...'

    db = mdb.connect('localhost', 'root', '', 'insight')
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

    curr_loc = [40.74844,-73.985664]
    radius = 0.005
    idx = (photos2['Lat']-curr_loc[0])**2 + (photos2['Lng']-curr_loc[1])**2 < radius ** 2

    duration = cluster_duration(photos2, curr_loc, idx)

    print 'estimated visit duration: %d hr' % duration/3600. 
    