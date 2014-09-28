import os, json, sys
import pymysql as mdb
import re
import pdb
import numpy as np
import pandas as pd
sys.path.append(os.path.abspath('flask_site/app/'))
from google_lookup import get_google_address

def parse_ranking(ustr):
    return int(ustr.split(' ')[1][1:])

def handle_theater(attr):
    if ('Theatre' in attr["name"]) or ('Theatre' in attr["street"]) or ('Theater' in attr["name"]) \
    or ('Theater' in attr["street"]):
        return True
    else:
        return False
# Examples:
# Stephen Sondheim Theatre
# August Wilson Theatre
# Minskoff Theatre
# Winter Garden Theatre
# Longacre Theatre
# Street Music Box Theatre
# Street Belasco Theatre
# National Comedy Theatre New York

# check whether input is within bounds 
def within_nyc_bounds(lat, lng):
    return (40.50 <= lat <= 41.00) and (-74.30 <= lng <= -73.60)


    # [u'activities', u'description', u'fee', u'length', u'name', u'ranking', 
    # u'rated_by', u'rating', u'review_breakdown', u'review_total', u'street', 
    # u'type', u'url', u'useful information']
def insert_tripadvisor_sql(attr,idx,init=True):
    con = mdb.connect('localhost', 'root', '', 'insight') #host, user, password, #database
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS tripadvisor")
            create_cmd = "CREATE TABLE tripadvisor(Id INT PRIMARY KEY, \
                activities VARCHAR(100), fee FLOAT, length VARCHAR(25), \
                name VARCHAR(100), ranking VARCHAR(50), rated_by VARCHAR(25), \
                rating FLOAT, review_total VARCHAR(50), street VARCHAR(200), \
                type VARCHAR(50), information VARCHAR(50))"
            cur.execute(create_cmd)

        cmd = "INSERT INTO tripadvisor (Id, activities, fee, length, name, ranking, rated_by, \
            rating, review_total, street, type, information) \
         VALUES (%d, '%s', %s, '%s', %s, '%s', '%s', %s, '%s', '%s', '%s', '%s') " \
         % (idx, attr['activities'], attr['fee'], attr['length'], attr['name'], attr['ranking'], attr['rated_by'],\
            attr['rating'], attr['review_total'], attr['street'], attr['type'], attr['information'])
        #pdb.set_trace()
        cur.execute(cmd)

def insert_map_sql(con,attr,idx,init=True):
    with con:
        cur = con.cursor()
        if init: # initialize table 
            cur.execute("DROP TABLE IF EXISTS tripadvisor_latlng")
            create_cmd = "CREATE TABLE tripadvisor_latlng(Entry INT PRIMARY KEY AUTO_INCREMENT, \
                Id INT, loc_lat DOUBLE, loc_lng DOUBLE, bounds_ne_lat DOUBLE, bounds_ne_lng DOUBLE, \
                    bounds_sw_lat DOUBLE, bounds_sw_lng DOUBLE, viewport_ne_lat DOUBLE, viewport_ne_lng DOUBLE, \
                    viewport_sw_lat DOUBLE, viewport_sw_lng DOUBLE)"
            cur.execute(create_cmd)

        if attr["street"] == "New York City, NY New York City, NY":
            lookupVal = attr['name']
            print 'Look up by Name!!!', lookupVal
        else:
            lookupVal = attr["street"]
        print lookupVal

        if lookupVal:
            results = get_google_address(lookupVal)
            if not results: # try looking up by name
                'no result, so looking up by name'
                results = get_google_address(attr["name"])
                pdb.set_trace()

            if results:
                for result in results:
                    loc = result['geometry']['location']
                    if not within_nyc_bounds(loc['lat'],loc['lng']):
                        print 'out of bounds'
                        print [name['short_name'] for name in result['address_components']]

                    if 'bounds' in result['geometry']:
                        bounds_ne = result['geometry']['bounds']['northeast'].values()
                        bounds_sw = result['geometry']['bounds']['southwest'].values()
                        do_str = False
                    else:
                        bounds_ne = ['null','null']
                        bounds_sw = ['null','null']
                        do_str = True
                    viewport_ne = result['geometry']['viewport']['northeast'].values()
                    viewport_sw = result['geometry']['viewport']['southwest'].values()

                    # insert into sql 
                    if do_str:
                        cmd = "INSERT INTO tripadvisor_latlng (Id, loc_lat, loc_lng, bounds_ne_lat, bounds_ne_lng, \
                           bounds_sw_lat, bounds_sw_lng, viewport_ne_lat, viewport_ne_lng, viewport_sw_lat, viewport_sw_lng) \
                           VALUES (%d, %.15g, %.15g, %s, %s, %s, %s, %.15g, %.15g, %.15g, %.15g) " \
                          % (idx, loc['lat'], loc['lng'], bounds_ne[0],bounds_ne[1],bounds_sw[0],bounds_sw[1],\
                          viewport_ne[0],viewport_ne[1],viewport_sw[0],viewport_sw[1])
                    else: 
                        cmd = "INSERT INTO tripadvisor_latlng (Id, loc_lat, loc_lng, bounds_ne_lat, bounds_ne_lng, \
                            bounds_sw_lat, bounds_sw_lng, viewport_ne_lat, viewport_ne_lng, viewport_sw_lat, viewport_sw_lng) \
                           VALUES (%d, %.15g, %.15g, %.15g, %.15g, %.15g, %.15g, %.15g, %.15g, %.15g, %.15g) " \
                           % (idx, loc['lat'], loc['lng'], bounds_ne[0],bounds_ne[1],bounds_sw[0],bounds_sw[1],\
                            viewport_ne[0],viewport_ne[1],viewport_sw[0],viewport_sw[1])
                    cur.execute(cmd)

if __name__ == '__main__':
    
    # load attractions from json 
    attractions = []
    tripid = range(1,30)
    for num in tripid:
        filename = 'tripadvisor_nyc%02d.json' % num
        #print 'loading', filename
        with open(os.path.join('tripdata',filename)) as fp:
            attractions.extend(json.load(fp))

    # convert to data frame 
    # [u'activities', u'description', u'fee', u'length', u'name', u'ranking', 
    # u'rated_by', u'rating', u'review_breakdown', u'review_total', u'street', 
    # u'type', u'url', u'useful information']
    get_ascii = lambda x : x.encode('ascii', 'ignore')
    attractions = pd.DataFrame(attractions)
    columns = ['description', 'name', 'street']
    for col in columns:
        attractions[col] = attractions[col].map(get_ascii)
    # do some massaging for now so this can be fit into sql. deal with later 
    del attractions['review_breakdown']
    attractions = attractions.fillna('null')

    # save into dataframe
    db = mdb.connect('localhost', 'root', '', 'insight')
    #pdb.set_trace()
    # okay this doesn't work. maybe we'll just work with json 
    #attractions.to_sql(name='tripadvisor',con=db,flavor='mysql',if_exists='replace')

    init = True
    for idx, attr in attractions.iterrows():
        print idx, '-------------------------------------------------'
        # this doesn't work 
        #insert_tripadvisor_sql(idx,attr,init=init)
        # figure out whether to look up by address or name
        if handle_theater(attr):
            print 'SKIPPING', attr['name'], attr['street']
            #pdb.set_trace()
            continue
        else:
            insert_map_sql(db,attr,idx,init=init)
        init = False

