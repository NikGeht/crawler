import crawler
import requests
Crawl = crawler.Crawler()
init_url = 'https://habr.com/ru/'
urlList = []
urlList.append(init_url)

Crawl.crawl(urlList=urlList, maxDepth=1)