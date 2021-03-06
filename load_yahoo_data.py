import os 
import bz2
import json
import pymysql as mdb
import pdb
import pandas as pd
import numpy as np
from datetime import datetime

def read_into_json(file_name, lat_bound=[40.60, 40.90], lng_bound=[-74.20,-73.70]):

    keys = ['id', 'user_id', 'user_name', 'date_taken', 'date_uploaded', 'device', 'title', \
    'description', 'user_tags', 'machine_tags','lng', 'lat', 'accuracy', 'page_url', 'download_url', \
    'license_name','license_url', 'server_id', 'farm_id', 'secret', 'secret_orig', 'extension_orig', \
    'video_marker']
    
    bz_file = bz2.BZ2File(file_name)
    line = bz_file.readline()
    linenum = 1
    photo_list = []
    while not (line == ''):
        # split tab-delimited line 
        line_vals = line.split('\t')

        # query by geo values 
        lng = line_vals[10]
        lat = line_vals[11]

        if lat: 
            lng = float(lng)
            lat = float(lat)
            # append if it's within bounding box 
            if ((lng > lng_bound[0]) and (lng < lng_bound[1])) and ((lat > lat_bound[0]) and (lat < lat_bound[1])):
                # create dictionary
                photo = {}
                for idx,val in enumerate(line_vals):
                    photo[keys[idx]] = val
                photo['lat'] = lat
                photo['lng'] = lng
                photo_list.append(photo)
                #pdb.set_trace()
                print repr(linenum) + ' ' + photo['title']
        
        # for debugging 
        # if linenum > 2000: break

        # keep reading 
        line = bz_file.readline()
        linenum +=1 

    print linenum-1
    return photo_list


def load_json(file_name):
    with open(file_name) as fp:
        photo_list = json.load(fp)
    return photo_list

def write_json(photo_list, file_name):
    print "No of photos: ", len(photo_list)
    with open(file_name, 'wb') as fp:
        fp.write(json.dumps(photo_list, separators=(',',':')))

def insert_loc_sql_tags(con, photos, init=True, name='flickr_yahoo_nyc_tags'):
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS "+ name)
            cur.execute("CREATE TABLE %s (Id VARCHAR(25), tag VARCHAR(150))" % name)
        for photo in photos:
            tags = photo['user_tags'].split(',')
            for tag in tags:
                if len(tag) > 150:
                    print 'tag too long: ', tag
                    continue
                else:
                    cmd = "INSERT INTO %s (Id, tag) VALUES ('%s', '%s')" % \
                    (name, photo['id'].encode('ascii','ignore'), tag)
                    #pdb.set_trace()
                    cur.execute(cmd)


def insert_loc_sql(con, photos,init=True, name = 'flickr_yahoo_nyc'):
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS "+ name)
            cur.execute("CREATE TABLE %s(Id VARCHAR(25) PRIMARY KEY, Lat FLOAT, Lng FLOAT, accuracy INT, \
                page_url VARCHAR(80), user_id VARCHAR(25), user_name VARCHAR(500), date_taken DATETIME, date_uploaded VARCHAR(25), \
                device VARCHAR(100), server_id INT, farm_id INT, secret VARCHAR(15), video_marker INT)" % name)
        for photo in photos:
            cmd = "INSERT INTO %s (Id, Lat, Lng, accuracy, page_url, user_id, user_name,\
                date_taken, date_uploaded, device, server_id, farm_id, secret, video_marker) \
                VALUES ('%s', %s, %s, %s, '%s', '%s', '%s', '%s', '%s', '%s', %s, %s, '%s', %s)" \
                % (name, photo['id'].encode('ascii','ignore'),photo['lat'], photo['lng'], photo['accuracy'], photo['page_url'], \
                    photo['user_id'],photo['user_name'].encode('ascii'),photo['date_taken'], photo['date_uploaded'],\
                    photo['device'], int(photo['server_id']), int(photo['farm_id']), photo['secret'], photo['video_marker'].encode('ascii').rstrip('\n'))
            cur.execute(cmd)

def _check_for_badidx(photo_df):
    # check for date time convertable 
    temp = pd.to_datetime(photo_df['date_taken'][0])
    badidx = np.zeros(shape = (photo_df.shape[0]))
    for idx,date in enumerate(photo_df['date_taken']):
        if type(pd.to_datetime(date)) != type(temp):
            print idx,date
            badidx[idx] = 1
    return badidx

def format_restrict_dataframe(photo_df):
    # check for date time convertable 
    badidx = _check_for_badidx(photo_df)
    # restrict data frame 
    photos2 = photo_df.ix[badidx == 0]
    # convert to date time and reset index 
    photos2.index = pd.to_datetime(photos2['date_taken'])
    # get photos within reasonable window
    photos2 = photos2.ix['2009':'2015']
    return photos2


if __name__ == '__main__':
    
    flickr_yahoo_path = 'flickr_yahoodata'
    lat_bound_nyc = [40.60, 40.90]
    lng_bound_nyc = [-74.20,-73.70]

    file_names = ["yfcc100m_dataset-0.bz2", "yfcc100m_dataset-1.bz2", "yfcc100m_dataset-2.bz2", "yfcc100m_dataset-3.bz2", \
    "yfcc100m_dataset-4.bz2", "yfcc100m_dataset-5.bz2", "yfcc100m_dataset-6.bz2", "yfcc100m_dataset-7.bz2", \
    "yfcc100m_dataset-8.bz2", "yfcc100m_dataset-9.bz2"]

    init = True
    load_from_rawfile = False

    con = mdb.connect('localhost', 'root', '', 'insight')
    for file_name in file_names:
        print file_name
        # get file name 
        full_file_name = os.path.join(flickr_yahoo_path,file_name)

        # specify json file name 
        (json_file_name,ext) = os.path.splitext(file_name)
        json_file_name = json_file_name + '_nyc.json'

        if load_from_rawfile:
            # load photo list 
            photo_list = read_into_json(full_file_name,lat_bound_nyc,lng_bound_nyc)
            # save into json
            write_json(photo_list, os.path.join(flickr_yahoo_path,json_file_name))
        else:
            photo_list = load_json(os.path.join(flickr_yahoo_path,json_file_name))

        # convert into data frame and restrict/format 
        photo_df = pd.DataFrame(photo_list)
        photo2 = format_restrict_dataframe(photo_df)

        # convert back into a list of dicts
        # ideally can just use pandas' photo2.to_sql function, but too lazy to figure it out 
        # first we need to reindex by something that's not time, so we don't lose the photos that have the same time stamp
        photo2.index = np.array(range(photo2.shape[0]))
        photo_list = photo2.T.to_dict().values()

        # insert into sql data base 
        #insert_loc_sql(con, photo_list,init)
        insert_loc_sql_tags(con, photo_list, init)
        print 'inserted into sql', file_name
        
        init = False
