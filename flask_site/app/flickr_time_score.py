import pandas as pd
import numpy as np
from datetime import datetime

def get_photo_density(photos,normalize=False):
    # convert to data frame 
    photo_df = pd.DataFrame(photos)
    # use time as an index
    photo_df.index = pd.to_datetime(photo_df['date_taken'])
    # get hour mean // NEED TO NORMALIZE BY TOTAL PHOTO COUNT
    hour_mean = photo_df.Id.groupby(lambda x: x.hour).count() 
    # normalize by group total 
    if normalize:
        hour_mean = hour_mean / float(photo_df.Id.count())
    # normalize by total photos taken 
    hour_mean = hour_mean.astype('float64') / _get_total_photo_density(normalize)
    return hour_mean

## TODO: HAND CODE FOR NOW, need to save into data base 
def _get_total_photo_density(normalize=False):
    photos_by_hour = [25872, 15102, 11771,  9836,  9052,  8434,  9993, 14671, 22276,\
       26439, 34341, 43772, 54410, 57102, 56773, 57608, 56338, 50621,\
       48689, 49202, 42919, 38819, 32505, 25750]
    total_photos = 802295.0
    photo_density = np.array(photos_by_hour) 
    if normalize:
        photo_density = photo_density / total_photos
    return photo_density

if __name__ == '__main__':
    import pymysql as mdb
    import matplotlib.pyplot as plt
    from flickr_sites import *
    import pdb

    init_loc = [40.74844,-73.985664]
    db = mdb.connect('localhost', 'root', '', 'insight')
    centroid_photos_withtime = get_timemap_sql(db,init_loc)
    fig = plt.figure()
    ax1 = fig.add_subplot(211)
    hour_mean = get_photo_density(centroid_photos_withtime)
    ax1.plot(hour_mean)
    ax2 = fig.add_subplot(212)
    hour_mean = get_photo_density(centroid_photos_withtime,True)
    ax2.plot(hour_mean)
    plt.show()
    pdb.set_trace()
