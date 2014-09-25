import pymysql as mdb
import pandas as pd
import numpy as np
import json
from flickr_sites import * 
import pdb
import matplotlib.pyplot as plt

# whether a location string a user inputs is in new york city or not 
def is_nyc_user(location_str):
    nyc_token = ['New York, NY', 'New York, New York', 'NYC', 'New York City', 'Brooklyn', 'BROOOOOOOOOKLYNNNN', 'BKYN', \
             'Queens', 'Manhattan', 'Astoria', 'Bronx', 'Bushwick', 'Forest Hills', "Hell's Kitchen", 'Hoboken',\
             'Jackson Heights', 'Jersey City', 'Long Island', 'Newark', 'Staten Island', 'Bayside', 'Harlem', 'East Village',\
             'New York , NY', 'New York NY', 'New York,  New York', 'New York,  NY', 'New York, US', 'New York, U.', \
             'New York, United States', 'New York, the U S of A', 'Newyork, USA']
    s_lower = location_str.lower()
    token_checker = [True if token.lower() in s_lower else False for token in nyc_token]
    token_checker.append((s_lower == 'new york') or (s_lower == 'new york ') or (s_lower == 'new york , usa') or \
                         (s_lower == 'new york, usa') or (s_lower == 'ny, usa') or (s_lower == 'ny'))
    return any(token_checker)


# similar to save_heatmap_clusters but this saves two tables 
# each corresponding to time scores of nyc users and nonnyc users 
if __name__ == '__main__':

    # get all the unique users and their associated locations 
    with open('../../nyc_user_location.json') as fp:
        user_locations = json.load(fp)
    print 'unique users', len(user_locations)

    # find all the unique users that are based in nyc 
    isnyc = np.array([ is_nyc_user(user_locations[p]) for p in user_locations])
    print 'new york users', sum(isnyc==True)

    # get all of the photos in data base 
    lim = 0.5
    db = mdb.connect('localhost', 'root', '', 'insight')
    photos2 = get_heatmap_sql(db,[40.74844,-73.985664],lim)
    photos2 = pd.DataFrame(photos2)
    print 'loaded %d photos from database' % photos2.shape[0]

    # figure out which of these are taken by nyc users
    isnyc = np.array([True if is_nyc_user(user_locations[p]) else False for p in photos2['user_id']])
    print '%s photos out of %s are nyc users' % (sum(isnyc), len(isnyc))

    #normalizer = pd.Series(np.ones(48),index=temp2.index)
    hour_all_nyc, photos_nyc = get_photo_density(photos2.ix[isnyc], interval=30, drop_duplicates=True)
    hour_all_out, photos_out = get_photo_density(photos2.ix[isnyc==False], interval=30, drop_duplicates=True)
    hour_all, photo_df = get_photo_density(photos2, interval=30, drop_duplicates=True)
    photos_nyc_n = photos_nyc.shape[0]
    photos_out_n = photos_out.shape[0]
    photos_n = photo_df.shape[0]
    print photos_nyc_n, photos_out_n

    # load centroids
    db = mdb.connect('localhost', 'root', '', 'insight')
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT * FROM flickr_clusters_nyc2")
        centroids = cur.fetchall()

    # for each centroid, find the time course for both nyc users and non nyc users
    # TODO: use cluster id rather than radius criterion 
    radius = 0.005
    init = True
    hour_score_n_nyc = []
    hour_score_list_nyc = []
    hour_score_n_out = []
    hour_score_list_out = []
    for cent in centroids:
        # get photos near centroid for new york users 
        idx_nyc = (photos_nyc['lat']-cent['lat'])**2 + (photos_nyc['lng']-cent['lng'])**2 < radius ** 2
        photos_nyc_cent  = photos_nyc.ix[idx_nyc]
        # get photos near centroid for outside users 
        idx_out = (photos_out['lat']-cent['lat'])**2 + (photos_out['lng']-cent['lng'])**2 < radius ** 2
        photos_out_cent  = photos_out.ix[idx_out]
        print 'number of photos near location: new york users %d, outsider users %d' % (sum(idx_nyc), sum(idx_out))
        # save the number of photos
        hour_score_n_nyc.append(sum(idx_nyc))
        hour_score_n_out.append(sum(idx_out))
        # get the hourly rate 
        #hour_score_nyc = compute_photo_timescore(photos_nyc_cent, hour_all_nyc, smooth=3)
        #hour_score_out = compute_photo_timescore(photos_out_cent, hour_all_out, smooth=3)
        hour_score_nyc = compute_photo_timescore(photos_nyc_cent, hour_all, smooth=3)/(photos_nyc_n/float(photos_n))
        hour_score_out = compute_photo_timescore(photos_out_cent, hour_all, smooth=3)/(photos_out_n/float(photos_n))
        # append to list 
        hour_score_list_nyc.append(hour_score_nyc)
        hour_score_list_out.append(hour_score_out)

    # convert to data frames 
    hour_score_list_nyc = pd.DataFrame(hour_score_list_nyc)
    hour_score_list_out = pd.DataFrame(hour_score_list_out)
    centroids = pd.DataFrame(centroids)

    hour_score_list_nyc.index = centroids.index
    hour_score_list_out.index = centroids.index

    # set the column names to the hour it is 
    time_axis = np.linspace(0,24,len(hour_all_nyc)+1)
    time_axis = time_axis[:-1]
    hour_score_list_nyc.columns = time_axis
    hour_score_list_out.columns = time_axis

    # add latitude longitude 
    hour_score_list_nyc['lat'] = centroids['lat']
    hour_score_list_nyc['lng'] = centroids['lng']
    hour_score_list_out['lat'] = centroids['lat']
    hour_score_list_out['lng'] = centroids['lng']

    # add the number of for photos for which it was computed
    hour_score_list_nyc['nphotos'] = hour_score_n_nyc
    hour_score_list_out['nphotos'] = hour_score_n_out

    # check for null values and fill them, otherwise can't input to sql 
    print 'number of nulls', [sum(hour_score_list_nyc[c].isnull()) for c in hour_score_list_nyc.columns],\
    [sum(hour_score_list_out[c].isnull()) for c in hour_score_list_out.columns]
    hour_score_list_nyc = hour_score_list_nyc.fillna(0)
    hour_score_list_out = hour_score_list_out.fillna(0)
    #hour_score_list_nyc = hour_score_list_nyc.fillna(method='pad', axis=1)
    #hour_score_list_out = hour_score_list_out.fillna(method='pad', axis=1)

    # save into sql databases
    hour_score_list_nyc.to_sql(name='flickr_clusters_nyc2_nycusers',con=db,flavor='mysql',if_exists='replace')
    hour_score_list_out.to_sql(name='flickr_clusters_nyc2_outusers',con=db,flavor='mysql',if_exists='replace')

