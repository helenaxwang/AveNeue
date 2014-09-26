import flickr
import pymysql as mdb
from load_yahoo_data import load_json, format_restrict_dataframe
import pdb
import os, json
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


# saves thumb nail urls into a sql data base for each centroid 
if __name__ == '__main__':
    import pdb
    cluster_by_id = True

    # load centroids
    db = mdb.connect('localhost', 'root', '', 'insight')
    with db:
        cur = db.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT * FROM flickr_clusters_nyc2")
        centroids = cur.fetchall()

    # load files from josn 
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

    print photo_df.shape

    # load centroids in data base which have cluster ids 
    if cluster_by_id:
        with db:
            cur = db.cursor(mdb.cursors.DictCursor)
            cur.execute("SELECT * FROM flickr_yahoo_nyc2")
            centroids_saved = cur.fetchall()
        centroids_saved = pd.DataFrame(centroids_saved)
        print centroids_saved.shape
    else:
        radius = 0.002
    
    # now find photos in the vicinity of each centroid 
    init = True
    for cent in centroids:
        curr_loc = (cent['lat'], cent['lng'])
        if cluster_by_id:
            idx = centroids_saved['cluster_label'] == cent['index']
            smallset = centroids_saved.ix[idx]
            smallset = pd.merge(smallset, photo_df, left_on='Id', right_on='id', how='left')
        else:
            idx = (photo_df['lat']-curr_loc[0])**2 + (photo_df['lng']-curr_loc[1])**2 < radius ** 2
            smallset  = photo_df.ix[idx]

        print cent['index'], curr_loc, smallset.shape[0]

        #t = thumb, s=small square, m = small 
        for idx, photo in smallset.iterrows():
            #print cent['index'], curr_loc, photo['id']
            url = "http://farm%s.static.flickr.com/%s/%s_%s_m.jpg" % (photo['farm_id'], photo['server_id'], photo['id'], photo['secret'])
            insert_centroids_thumbnail_sql(db,cent['index'],photo_id=photo['id'],url=url,init=init)
            init = False 
    print 'inserted into flickr_clusters_nyc2_thumb table!'
