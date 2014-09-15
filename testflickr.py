#import oauth2 as oauth
#import urllib2 as urllib
import flickr_api 
from flickr_api.api import flickr
from xml.etree import ElementTree as ET
import json

api_key = 'd82ac1545bb78f282a8d0a3f0c4f56d6'
api_secret = 'ab0e7e7fd22dce24'
flickr_api.set_keys(api_key=api_key,api_secret=api_secret)
#print flickr.reflection.getMethodInfo(method_name = "flickr.photos.getInfo")

'''
# authentication 
# https://github.com/alexis-mignon/python-flickr-api/wiki/Tutorial
a = flickr_api.auth.AuthHandler() #creates the AuthHandler object
# a = flickr_api.auth.AuthHandler(callback = "http://www.mysite.com/get_verifier/")
perms = "read" # set the required permissions
url = a.get_authorization_url(perms)
#print url
a.set_verifier("f47f372ab46ec5f2")
flickr_api.set_auth_handler(a)
a.save('flickr_auth')
# next time just do 
#a = flickr_api.auth.AuthHandler.load('flickr_auth')
#flickr_api.set_auth_handler(a)
#flickr_api.set_auth_handler('flickr_auth')

lat = 37.8081103
lon = -122.416631
accuracy = 16
photos = flickr.photos.geo.photosForLocation(api_key=api_key, lat=lat,lon=lon,accuracy=accuracy)
'''

# https://www.flickr.com/services/api/flickr.photos.search.html
# The 4 values represent the bottom-left corner of the box and the top-right corner
# minimum_longitude, minimum_latitude, maximum_longitude, maximum_latitude. 
delta = 0.01
bbox = '%s,%s,%s,%s'%(lon-delta,lat-delta,lon+delta,lat+delta)
photos = flickr.photos.search(api_key=api_key,bbox=bbox,accuracy=16,format='json')
#root = ET.fromstring(photos)
#------------------------------------------------------------------
# flickr.places.find(query='New York City')
# <place place_id=".skCPTpTVr.Q3WKW" woeid="2459115" latitude="40.714" longitude="-74.007" place_url="/United+States/New+York/New+York" place_type="locality" place_type_id="7" timezone="America/New_York" woe_name="New York City">

import flickr
import urllib2 as urllib
from PIL import Image
import os 

delta = 0.01
bbox = '%s,%s,%s,%s'%(lon-delta,lat-delta,lon+delta,lat+delta)
photos = flickr.photos_search(bbox=bbox,accuracy=16,per_page=200)
photos = flickr.photos_search(woe_id="2459115")

def load_photo(url):
    file, mime = urllib.urlretrieve(url)
    photo = Image.open(file)
    return photo

# # gets url for the list of photos
# def getPhotoURLs(photos):
#     urls = []
#     for photo in photos:
#         try:
#             urls.append(photo.getURL(size='Small', urlType='source'))
#         except flickr.FlickrError:
#             if verbose:
#                 print "%s has no URL" % (photo)
#     return urls
# urls = getPhotoURLs(photos)

# save photos for fact checking 
tmpdir = 'tmp'
for i,photo in enumerate(photos):
    fav = photo.getFavoriteCount()
    if int(fav) > 0:
        url = photo.getURL(size='Small', urlType='source')
        filename = 'img%02d_favcount%s.jpg'%(i,fav)
        photo = load_photo(url)
        photo.save(os.path.join(tmpdir, filename))

import pandas as pd
import matplotlib.pyplot as plt
flickrphotos =  pd.read_csv('flickr_photos.csv',header=None)
flickrphotos.columns=['lat','lng','fav']
plt.hist(flickrphotos['fav'],bins=50)
plt.yscale('log')
plt.xlabel('Favorite counts')
plt.ylabel('Frequency')


