#!/usr/local/bin/env python
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
import random, time
import pprint 
import pdb
import json

browser = webdriver.Firefox()

def load_website_nyc():
    global browser 
    #browser = webdriver.Chrome(executable_path = '/Users/Helena/Projects/Insight/selenium_test/chromedriver')
    # go to wbesite for new york city and navigate through landing page 
    url = 'http://www.tripomatic.com/trip-planner/#/?destination=city:186'
    browser.get(url)
    #browser.find_element_by_id('wizard-form').send_keys('New York City')
    browser.find_element_by_xpath('//*[@id="js-wizard-2"]/div[3]/div[1]/div/a[2]').click()
    browser.find_element_by_xpath('//*[@id="js-create-trip"]').click()

# get all xpath elements using a while loop 
def _find_element_by_xpath_while_loop(xpath_string):
    n = 1
    vals = []
    while True:
        try :
            xpath_tag = '%s[%d]' % (xpath_string,n)
            vals.append(browser.find_element_by_xpath(xpath_tag).text)
        except NoSuchElementException as e:
            break
        n += 1
    return vals


def get_item_info(item_num):

    # top level xpath 
    item_xpath = '//*[@id="js-sidebar"]/ul/li[%d]/activity/b' % item_num
    # click on the side bar item to expand
    browser.find_element_by_xpath(item_xpath).click()
    # the expanded panel xpath base 
    base_xpath = '/html/body/div[2]/div[2]/div/div/div[1]/div[1]/activity-detail/div[5]/'

    loc = {}
    # get name
    loc['name'] = browser.find_element_by_xpath(base_xpath+'div[1]/div[2]/h2').text
    print 'Querying '+loc['name']
    # all tags associated with the site
    loc['tags'] = _find_element_by_xpath_while_loop(base_xpath+'div[2]/span/span')
    # get description text
    loc['text'] = _find_element_by_xpath_while_loop(base_xpath+'/div[2]/div[2]/p')
    loc['hours'] = browser.find_element_by_xpath(base_xpath+'/div[2]/div[4]/p').text
    loc['admission'] = browser.find_element_by_xpath(base_xpath+'/div[2]/div[5]/p').text

    print '\t Getting related Sites'
    # get all related sites 
    n = 1
    related_sites = []
    while True:
        try :
            xpath_tag = '%sdiv[2]/div[3]/ul/li[%d]/activity/span[2]/b' % (base_xpath,n)
            relsite = browser.find_element_by_xpath(xpath_tag).text
            related_sites.append(relsite)
        except NoSuchElementException: #CannotSendRequest
            break
        n += 1
    loc['related_locs'] = related_sites

    # get all attributes
    print '\t Getting additional attributes'
    n = 1
    attr = []
    while True:
        try :
            xpath_tag = '%sdiv[2]/p[4]/a[%d]' % (base_xpath,n)
            attr_name = browser.find_element_by_xpath(xpath_tag).get_attribute('class')
            text = browser.find_element_by_xpath(xpath_tag).text
            href = browser.find_element_by_xpath(xpath_tag).get_attribute('href')
            attr.append([attr_name,text,href])
            if 'location' in attr_name:
                loc['address'] = text
        except NoSuchElementException: 
            break
        n += 1
    loc['attributes'] = attr

    return loc


def main():
    global browser 
    load_website_nyc()
    browser.implicitly_wait(30)

    # initialize for writing to file 
    file_name = 'tripmatic_nyc.json'
    with open(file_name, 'wb') as fp:
        fp.write('[')

    i = 1
    while True:
        try : 
            loc = get_item_info(i)
            seconds = 0.5 + (random.random() * 1)
            time.sleep(seconds)
            print '-------- Location %d ---------' % i
            pprint.pprint(loc)
            print '------------------------------' 
            i += 1
            with open(file_name,'a') as fp:
                json.dump(loc,fp)
        except Exception as e:
            pdb.set_trace()
            break
        with open(file_name,'a') as fp:
            fp.write(',')

    with open(file_name,'a') as fp:
        fp.write(']')

if __name__ == "__main__":
    main()
