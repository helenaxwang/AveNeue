import os 
import json
import pymysql as mdb
import pdb
import datetime
import pprint
import numpy as np
from google_lookup import get_google_address

def parse_address(ustr):
    address_str = ustr.encode('ascii','ignore')
    if address_str:
        address_str = address_str.lstrip('Address\n').lstrip(' ')
    return address_str

# get all listed prices, do not distinguish status 
def parse_admission(ustr):
    admission_str = ustr.encode('ascii','ignore')
    cost = []
    if admission_str:
        admission_str = admission_str.split('\n')
        #admission_str = admission_str.split(' ')
        for adm in admission_str:
            if 'free' in adm.lower():
                cost.append(0)
            elif '$' in adm:
                #cost.append(float(adm.lower().lstrip('adults: $')))
                adm2 = adm.split(' ')
                for adm2a in adm2:
                    try: 
                        tmp = adm2a.find('$')
                        if tmp != -1:
                            cost.append(float(adm2a[tmp+1:]))
                    except Exception as e:
                        print e
                        continue
    return cost

# TODO: Add in hours 
# def parse_hours(ustr):
#     hour_str = ustr.encode('ascii','ignore')
#     if hour_str:
#         hour_str_list = hour_str.split('\n\n')
#         if {"every day", "daily"} in hour_str_list[0]

def format_attraction(attraction):
    attr = {}
    attr['address'] = parse_address(attraction['address'])
    attr['admission'] = parse_admission(attraction['admission'])
    attr['hours'] = ''
    attr['name'] = attraction['name'].encode('ascii','ignore')
    attr['tags'] = attraction['tags'][1:]
    # to do: may have more than 1 field, detailed description. to do natural language processing
    attr['text'] = attraction['text'][0].encode('ascii','ignore')
    return attr 

# TODO: add a separate table of tags 
def insert_tripomatic_sql(attr,idx,init=True):
    con = mdb.connect('localhost', 'root', '', 'insight') #host, user, password, #database
    with con:
        cur = con.cursor()
        if init:
            cur.execute("DROP TABLE IF EXISTS tripomatic")
            create_cmd = "CREATE TABLE tripomatic(Id INT PRIMARY KEY, \
                Name VARCHAR(50), Address VARCHAR(500), Admission FLOAT, Desciption VARCHAR(500))"
            cur.execute(create_cmd)
        admission = np.mean(attr['admission'])
        
        if np.isnan(admission):
            admission = 'null'

        cmd = "INSERT INTO tripomatic (Id, Name, Address,Admission) VALUES (%d, '%s', '%s', %s) " \
         % (idx, attr['name'].replace('\'',''), attr['address'], admission)
        #pdb.set_trace()
        cur.execute(cmd)


def insert_map_sql(attr,idx,init=True):
    con = mdb.connect('localhost', 'root', '', 'insight')
    with con:
        cur = con.cursor()
        if init: # initialize table 
            cur.execute("DROP TABLE IF EXISTS tripomatic_latlng")
            create_cmd = "CREATE TABLE tripomatic_latlng(Entry INT PRIMARY KEY AUTO_INCREMENT, \
                Id INT, loc_lat DOUBLE, loc_lng DOUBLE, bounds_ne_lat DOUBLE, bounds_ne_lng DOUBLE, \
                    bounds_sw_lat DOUBLE, bounds_sw_lng DOUBLE, viewport_ne_lat DOUBLE, viewport_ne_lng DOUBLE, \
                    viewport_sw_lat DOUBLE, viewport_sw_lng DOUBLE)"
            cur.execute(create_cmd)

        # figure out whether to look up by address or name 
        if attr["address"]:
            lookupVal = attr["address"]
        else:
            lookupVal = attr['name']
            print 'Look up by Name!!!'
        if lookupVal:
            results = get_google_address(lookupVal)
            if results:
                for result in results:
                    loc = result['geometry']['location']
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
                        cmd = "INSERT INTO tripomatic_latlng (Id, loc_lat, loc_lng, bounds_ne_lat, bounds_ne_lng, \
                           bounds_sw_lat, bounds_sw_lng, viewport_ne_lat, viewport_ne_lng, viewport_sw_lat, viewport_sw_lng) \
                           VALUES (%d, %.15g, %.15g, %s, %s, %s, %s, %.15g, %.15g, %.15g, %.15g) " \
                          % (idx, loc['lat'], loc['lng'], bounds_ne[0],bounds_ne[1],bounds_sw[0],bounds_sw[1],\
                          viewport_ne[0],viewport_ne[1],viewport_sw[0],viewport_sw[1])
                    else: 
                        cmd = "INSERT INTO tripomatic_latlng (Id, loc_lat, loc_lng, bounds_ne_lat, bounds_ne_lng, \
                            bounds_sw_lat, bounds_sw_lng, viewport_ne_lat, viewport_ne_lng, viewport_sw_lat, viewport_sw_lng) \
                           VALUES (%d, %.15g, %.15g, %.15g, %.15g, %.15g, %.15g, %.15g, %.15g, %.15g, %.15g) " \
                           % (idx, loc['lat'], loc['lng'], bounds_ne[0],bounds_ne[1],bounds_sw[0],bounds_sw[1],\
                            viewport_ne[0],viewport_ne[1],viewport_sw[0],viewport_sw[1])
                    cur.execute(cmd)
                

if __name__ == '__main__':
    
    with open(os.path.join('selenium_scraper','tripmatic_nyc.json')) as fp:
        attractions = json.load(fp)

    init = True
    for idx, attraction in enumerate(attractions):
        #if idx < 80: continue
        attr = format_attraction(attraction)
        print '%d ----------------------------' % idx 
        # print 'hours :' , attraction['hours']
        # print '----------------------------'
        # print 'admission : ' , attraction['admission']
        # print '----------------------------'
        pprint.pprint(attr)
        # populate two data bases
        # first has information scraped from tripomatic website
        # second has google maps information using a lookup by address/name
        insert_tripomatic_sql(attr,idx,init)
        insert_map_sql(attr,idx,init)
        init = False
        if not attr['name']:
            pdb.set_trace()

