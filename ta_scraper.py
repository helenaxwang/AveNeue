#!/usr/local/bin/env python

import requests
from bs4 import BeautifulSoup
#from selenium import webdriver
#from lxml import etree
#import StringIO
import json
import pprint 
import random, time
import pdb


def get_pages(url='/Attractions-g60763-Activities-New_York_City_New_York.html',num=1):
    
    baseurl = 'http://www.tripadvisor.com'
    page = requests.get(baseurl+url)
    soup = BeautifulSoup(page.text)

    ta_site_list = []
    # get the initial list of 30 
    site_list = soup.find('div', attrs={'id': "ATTRACTION_OVERVIEW"}).findAll('div',attrs={'class': "quality easyClear"})
    ta_site_list = []
    for site in site_list:
        
        ta_site = {}
        ta_site['name'] = site.find('a').text
        ta_site['url'] = site.find('a').get('href')
        print ta_site['name'] + '   ' + ta_site['url']
        # open the next page 
        subpage = requests.get(baseurl+ta_site['url'])
        subsoup = BeautifulSoup(subpage.text)
        
        # get the address 
        address_xml = subsoup.find('div', attrs={'class': "wrap infoBox"}).find('span',attrs={'rel':"v:address"}).findAll('span')
        if address_xml: 
            ta_site['street'] = address_xml[1].text.encode('utf8') + ' ' + address_xml[2].text.encode('utf8') + ', ' + address_xml[3].text.encode('utf8')

        # get ranking 
        try : 
            ta_site['ranking'] = subsoup.find('div',attrs={'class':"popRanking wrap"}).find('div').text
        except Exception as e:
            print e

        # get rating
        try : 
            ta_site['rating'] = subsoup.find('div',attrs={'class':"rs rating"}).find('img').get('content')
        except Exception as e:
            print e

        # how many people 
        try : 
            ta_site['rated_by'] = subsoup.find('div',attrs={'class':"rs rating"}).text.strip('\n')
        except Exception as e:
            print e

        info_xml = subsoup.find('div',attrs={'class':"listing_details"}).findAll('div',attrs={'class':"detail"})
        for info in info_xml:
            key = info.find('b').text
            val = info.get_text().strip('\n').lstrip(key)
            key = key.rstrip(':').lower()
            if 'length' in key:
                key = 'length'
            ta_site[key] = val

        # description: maybe follow up later with better text processing
        # also has a 'more' link -- should follow up, plus saving hyperlinks 
        try : 
            ta_site['description'] = subsoup.find('div',{'class': "listing_description"}).text
        except Exception as e:
            print e

        # reviews 
        try : 
            ta_site['review_total'] = subsoup.find(id="REVIEWS").find('h3').text
        except Exception as e:
            print e

        # review breakdown
        review_breakdown = {}
        review_key = subsoup.find('fieldset').findAll('span',attrs={'class':"text"})
        review_count = subsoup.find('fieldset').findAll('span',attrs={'class':"compositeCount"})       
        if review_key:
            for r in range(5):
                review_breakdown[review_key[r].text] = review_count[r].text

        ta_site['review_breakdown'] = review_breakdown

        pprint.pprint(ta_site)
        ta_site_list.append(ta_site)
    
    write_pages(ta_site_list, num)
    #return ta_site_list

    next_url_xml = soup.find('a',attrs={'class': "guiArw sprite-pageNext "})
    return next_url_xml

def write_pages(ta_site_list,num=1):
    file_name = 'tripdata/tripadvisor_nyc%02d.json' % num
    with open(file_name, 'wb') as fp:
        fp.write(json.dumps(ta_site_list,separators=(',',':')))

def main():
    init_url = '/Attractions-g60763-Activities-New_York_City_New_York.html'
    pagenum = 1
    while True:
        new_url_xml = get_pages(init_url,pagenum)
        if not new_url_xml:
            break
        elif:
            init_url = new_url_xml.get('href')
        pagenum+=1
        seconds = 0.5 + (random.random() * 1)
        time.sleep(seconds)


    #pdb.set_trace()
    
if __name__ == "__main__":
    main()
