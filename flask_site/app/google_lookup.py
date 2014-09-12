import urllib, json
import pymysql as mdb
import pprint
import pdb
#%reload_ext autoreload

def get_google_address(address):
    google_api_key = 'AIzaSyAfaYz3fgaT4GA2rLb_iF3nbpUoo8-e1Ss'
    address_formatted = '+'.join(address.split(' '))
    base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    address_request = 'address=' + address_formatted
    api_request = '&key=' + google_api_key
    complete_url = base_url + address_request + api_request 

    googleResponse = urllib.urlopen(complete_url)
    jsonResponse = json.loads(googleResponse.read())
    if jsonResponse['status'] == 'OK':
        results = jsonResponse['results']
        if len(results) > 1:
            print 'Warning, more than one result returned!!!!'
            #pdb.set_trace()
    #pprint.pprint(results)
    return results

if __name__ == '__main__':

    con = mdb.connect('localhost', 'root', '', 'insight')
    with con:
        cur = con.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT Id, Name, Address FROM tripomatic")
        rows = cur.fetchall()
        for row in rows:
            print '\n====================================='
            print row["Id"], row["Name"]
            print row["Address"]
            if row["Address"]:
                lookupVal = row["Address"]
            else:
                lookupVal = row['Name']
                print 'Look up by Name!!!'
            if lookupVal:
                results = get_google_address(lookupVal)
                for result in results:
                    print '----------------------------------'
                    #print.pprint(result['geometry']['location'])
                    pprint.pprint(result['geometry'])
                    pdb.set_trace()