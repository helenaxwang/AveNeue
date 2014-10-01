import flickr
import pymysql as mdb

def get_flickr_fav(photo_id):
    method = 'flickr.photos.getFavorites'
    data = flickr._doget(method, photo_id=photo_id)
    return int(data.rsp.photo.total)

def get_flickr_views(photo_id):
    method = 'flickr.photos.getInfo'
    data = flickr._doget(method, photo_id=photo_id)
    return int(data.rsp.photo.views)

def insert_flickr_favorites(con, photo_id, fav_counts, init=False, doReplace='INSERT'):
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS flickr_favorites")
            create_cmd = "CREATE TABLE flickr_favorites(Id VARCHAR(25) PRIMARY KEY, Fav INT)"
            cur.execute(create_cmd)        
        cmd = "%s INTO flickr_favorites (Id, Fav) VALUES ('%s', %s) " % (doReplace, photo_id, fav_counts)
        cur.execute(cmd)

def fetch_flickr_favorites(con,photo_id):
    with con:
        cur = con.cursor()
        cmd = "SELECT * FROM flickr_favorites WHERE Id = '%s'" % photo_id
        cur.execute(cmd)
        photos = cur.fetchall()
    return photos


if __name__ == '__main__':
    import pdb

    init_loc = [40.7298482,-73.9974519]
    lim = 0.5
    # 345123
    db = mdb.connect('localhost', 'root', '', 'insight')
    with db:
        cur = db.cursor()
        cmd = "SELECT Id, page_url FROM flickr_yahoo_nyc WHERE date_taken >= '2010/01/01' AND \
        ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
        (init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
        cur.execute(cmd)
        photos = cur.fetchall()

    print '%d photos found' % len(photos)
    init = False # set this to false immediately after 
    for idx, photo in enumerate(photos):
        if idx % 100 == 0:
            print idx

        # if we already queried this, don't need to again 
        stored_photo = fetch_flickr_favorites(db,photo[0])

        if stored_photo:# and stored_photo[0][1] is not None:
            continue
        
        try:
            fav_counts = get_flickr_fav(photo[0])
            insert_flickr_favorites(db, photo[0], fav_counts, init=init)
        except Exception as e:
            print e
            print photo
            if 'Photo not found' in e.message:
                insert_flickr_favorites(db, photo[0], 'null', init=init)
        init = False
