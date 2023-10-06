import crawler
import requests
Crawl = crawler.Crawler()
init_url = 'https://habr.com/ru/articles/'
urlList = []
urlList.append(init_url)

Crawl.crawl(urlList=urlList, maxDepth=2)