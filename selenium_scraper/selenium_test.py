from selenium import webdriver
from selenium.webdriver.common.keys import Keys

browser = webdriver.Firefox()
browser.get('http://www.yahoo.com')
assert 'Yahoo' in browser.title

elem = browser.find_element_by_name('p')  # Find the search box
elem.send_keys('seleniumhq' + Keys.RETURN) # search in yahoo seleniumhq

browser.quit()

#-----------------------
# http://thiagomarzagao.com/2013/11/12/webscraping-with-selenium-part-1/

path_to_chromedriver = '/Users/Helena/Projects/Insight/selenium_test/chromedriver'
browser = webdriver.Chrome(executable_path = path_to_chromedriver)

url = 'https://www.lexisnexis.com/hottopics/lnacademic/?verb=sf&amp;sfi=AC00NBGenSrch'
browser.get(url)
browser.switch_to_frame('mainFrame')
browser.find_element_by_id('terms')
browser.find_element_by_id('terms').clear()
browser.find_element_by_id('terms').send_keys('balloon')
browser.find_element_by_xpath('//*[@id="dateSelector1"]')
browser.find_element_by_xpath('//*[@id="srchButt"]').click()


