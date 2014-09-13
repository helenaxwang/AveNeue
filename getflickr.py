#!/usr/bin/env python
import os 
import pprint
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pymysql as mdb

# load flickr json from files
def read_flickrphotos_byfilename(filename):
    with open(file_name) as fp:
        photos = json.load(fp)
    fp.close()
    return photos

def insert_loc_sql(photos):
    con = mdb.connect('localhost', 'root', '', 'insight') #host, user, password, #database
    with con:
        cur = con.cursor()
        cur.execute("DROP TABLE IF EXISTS flickr")
        cur.execute("CREATE TABLE flickr(Id VARCHAR(25) PRIMARY KEY, Lat FLOAT, Lng FLOAT, Fav INT)")
        for photo in photos:
            cmd = "INSERT IGNORE INTO flickr (Id, Lat, Lng, Fav) VALUES ('%s', %s, %s, %d) " \
             % (photo['id'].encode('ascii','ignore'),photo['lat'],photo['lng'],photo['fav_count'])
            cur.execute(cmd)

def fetch_loc_sql():
    con = mdb.connect('localhost', 'root', '', 'insight')
    with con:
        cur = con.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT * FROM flickr LIMIT 50")
        rows = cur.fetchall()
        for row in rows:
            print row["Id"], row["Lat"], row["Lng"], row["Fav"]

if __name__ == '__main__':
    
    pagenum = 110
    file_name = 'nyc_%03d.json' % pagenum
    file_name = os.path.abspath(os.path.join('flickr_crawler','flickr_nyc', file_name))
    pprint.pprint(file_name)
    photos = read_flickrphotos_byfilename(file_name)

    # insert into sql 
    insert_loc_sql(photos)

    # load into data frame 
    df = pd.DataFrame(photos)

    # plot the distribution of views
    df['views'].astype(float).hist(bins=30)

    # plot the favorite count 
    df['fav_count'].astype(float).hist(bins=30)
    plt.yscale('log')

