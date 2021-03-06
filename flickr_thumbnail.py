import flickr
import pymysql as mdb
from load_yahoo_data import load_json, format_restrict_dataframe
import pdb
import os, json, urllib2
import pandas as pd

def insert_centroids_thumbnail_sql(con,idx,photo_id,url,init=True):
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS flickr_clusters_nyc2_thumb")
            cur.execute("CREATE TABLE flickr_clusters_nyc2_thumb(entry Int PRIMARY KEY AUTO_INCREMENT, \
                ClusterId Int, Id VARCHAR(25), url VARCHAR(100))")
        cmd = "INSERT INTO flickr_clusters_nyc2_thumb (ClusterId, Id, url) VALUES (%s, '%s', '%s')" % (idx, photo_id, url)
        cur.execute(cmd)

def insert_thumbnail_sql(con, photo_id, has_thumb, init=False, name="flickr_nyc_thumb"):
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS " + name)
            create_cmd = "CREATE TABLE %s (id VARCHAR(25) PRIMARY KEY, has_thumb INT)" % name
            cur.execute(create_cmd)        
        cmd = "INSERT INTO %s (id, has_thumb) VALUES ('%s', %s) " % (name, photo_id, has_thumb)
        cur.execute(cmd)

# checks if redirected url is 'https://s.yimg.com/pw/images/photo_unavailable_m.gif'
def get_redirected_url(url):
    opener = urllib2.build_opener(urllib2.HTTPRedirectHandler)
    request = opener.open(url)
    return request.url

# saves thumb nail urls into a sql data base for each centroid 
if __name__ == '__main__':
    import pdb
    cluster_by_id = True
    load_from_raw = False
    save_by_centroid = True

    # load centroids
    db = mdb.connect('localhost', 'root', '', 'insight')
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT * FROM flickr_clusters_nyc2")
        centroids = cur.fetchall()
        # load centroids in data base which have cluster ids 
        if cluster_by_id:
            cur.execute("SELECT * FROM flickr_yahoo_nyc2")
            centroids_saved = cur.fetchall()
            centroids_saved = pd.DataFrame(centroids_saved)
            print centroids_saved.shape

    if load_from_raw:
        # load files from json 
        flickr_yahoo_path = 'flickr_yahoodata'
        file_names = ["yfcc100m_dataset-0.bz2", "yfcc100m_dataset-1.bz2", "yfcc100m_dataset-2.bz2", "yfcc100m_dataset-3.bz2", \
            "yfcc100m_dataset-4.bz2", "yfcc100m_dataset-5.bz2", "yfcc100m_dataset-6.bz2", "yfcc100m_dataset-7.bz2", \
            "yfcc100m_dataset-8.bz2", "yfcc100m_dataset-9.bz2"]

        # get all photo list 
        photo_list_all = []
        for file_name in file_names:
            # specify json file name 
            (json_file_name,ext) = os.path.splitext(file_name)
            json_file_name = json_file_name + '_nyc.json'
            print json_file_name

            photo_list = load_json(os.path.join(flickr_yahoo_path,json_file_name))
            photo_list_all.extend(photo_list)

        # convert into data fram and restrict format 
        photo_df = pd.DataFrame(photo_list_all)
        photo_df = format_restrict_dataframe(photo_df)
    
    else:
        with db:
            cur = db.cursor(mdb.cursors.DictCursor)
            cur.execute("SELECT * FROM flickr_yahoo_nyc WHERE user_name != 'atlanticyardswebcam04'")
            photo_list_all = cur.fetchall()
        photo_df = pd.DataFrame(photo_list_all)

    print photo_df.shape

    # now find photos in the vicinity of each centroid 
    if save_by_centroid:
        init = True
        for cent in centroids:
            curr_loc = (cent['lat'], cent['lng'])
            if cluster_by_id:
                idx = centroids_saved['cluster_label'] == cent['index']
                smallset = centroids_saved.ix[idx]
                smallset = pd.merge(smallset, photo_df, left_on='Id', right_on='Id', how='left')
            else:
                radius = 0.002
                idx = (photo_df['Lat']-curr_loc[0])**2 + (photo_df['Lng']-curr_loc[1])**2 < radius ** 2
                smallset  = photo_df.ix[idx]

            print cent['index'], curr_loc, smallset.shape[0]

            #t = thumb, s=small square, m = small 
            for idx, photo in smallset.iterrows():
                #print cent['index'], curr_loc, photo['id']
                url = "http://farm%s.static.flickr.com/%s/%s_%s_m.jpg" % (photo['farm_id'], photo['server_id'], photo['Id'], photo['secret'])
                # checks for if url is available -- maybe really slow 
                #if 'photo_unavailable' not in get_redirected_url(url):
                insert_centroids_thumbnail_sql(db,cent['index'],photo_id=photo['Id'],url=url,init=init)
                #else:
                #print 'photo unavailable'
                init = False
        print 'inserted into flickr_clusters_nyc2_thumb table!'

    # figure out whether a given photo has a thumbnail, for all photos in database
    else:
        init = False
        print 'start collecting photos'
        for idx, photo in photo_df.iterrows():   
            url = "http://farm%s.static.flickr.com/%s/%s_%s_m.jpg" % (photo['farm_id'], photo['server_id'], photo['Id'], photo['secret'])
            try:
                if 'photo_unavailable' in get_redirected_url(url) or photo['video_marker'] == 1:
                    insert_thumbnail_sql(db,photo['Id'],0,init=init)
                else:
                    insert_thumbnail_sql(db,photo['Id'],1,init=init)
            except Exception as e:
                print e
                print photo
            init = False
            if idx % 100 == 0:
                print idx

