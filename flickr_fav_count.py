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

def insert_flickr_favorites(con, photo_id, fav_counts, init=False):
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS flickr_favorites")
            create_cmd = "CREATE TABLE flickr_favorites(Id VARCHAR(25) PRIMARY KEY, Fav INT)"
            cur.execute(create_cmd)        
        cmd = "INSERT INTO flickr_favorites (Id, Fav) VALUES ('%s', %d) " % (photo_id, fav_counts)
        cur.execute(cmd)

if __name__ == '__main__':
    import pdb

    init_loc = [40.7298482,-73.9974519]
    lim = 0.15
    # 345123
    db = mdb.connect('localhost', 'root', '', 'insight')
    with db:
        cur = db.cursor()
        cmd = "SELECT Id FROM flickr_yahoo_nyc WHERE date_taken >= '2012/01/01' AND \
        ((lat BETWEEN %s AND %s) AND (lng BETWEEN %s AND %s))" % \
        (init_loc[0]-lim,init_loc[0]+lim,init_loc[1]-lim,init_loc[1]+lim)
        cur.execute(cmd)
        photos = cur.fetchall()

    print '%d photos found' % len(photos)
    init = True # set this to false immediately after 
    for photo in photos:
        fav_counts = get_flickr_fav(photo[0])
        insert_flickr_favorites(db, photo[0], fav_counts, init=init)
        init = False
