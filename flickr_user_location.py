import flickr
# import csv 
import pymysql as mdb
import pandas as pd
import json

def get_flickr_fav(user_id):
    method = 'flickr.people.getInfo'
    data = flickr._doget(method, user_id=user_id)
    return data.rsp.person.location.text

if __name__ == '__main__':
    import pdb

    # load flickr photos from database
    print 'loading from flickr_yahoo_nyc data base...'
    db = mdb.connect('localhost', 'root', '', 'insight')
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cmd = "SELECT * FROM flickr_yahoo_nyc "
        cur.execute(cmd)
        photos = cur.fetchall()
    
    # convert into a data frame 
    print 'converting to data frame'
    photos2= pd.DataFrame(photos)

    # get unique users who have taken photos in nyc
    unique_users = photos2['user_id'].unique()
    print 'unique users =', len(unique_users)

    # get user location for those users
    print 'getting user locations'
    locations = {}
    for user_id in unique_users:
        try:
            loc = get_flickr_fav(user_id=user_id)
            print loc
        except Exception as e:
            print e
        locations[user_id] = loc
    
    # with open('nyc_user_location.csv', 'wb') as fp:
    #     wr = csv.writer(fp)
    #     wr.writerow(locations)
    with open('nyc_user_location.json', 'wb') as fp:
        fp.write(json.dumps(locations, separators=(',',':')))
