from bs4 import BeautifulSoup
import sqlite3
import requests
from urllib.parse import urljoin

class Crawler(object):

    def __init__(self, dbFileName='crawler-db.db'):
        print('Constructor Crawler')
        self.conn = sqlite3.connect(dbFileName)
        self.cursor = self.conn.cursor()
        self.initDB()
        

    def __del__(self):
        self.cursor.close()
        self.conn.close()
        print('Destructor')


    def addURlList(self, url):
        self.cursor.execute('INSERT INTO URLList (URL) VALUES (?)', (url,))
        self.conn.commit()

    def addToIndex(self, soup: BeautifulSoup, url):
        if self.isIndexed(url):
            return 1
        else:
            text = self.getTextOnly(soup)
            urlid = self.getEntryId('urllist', 'url', url, True)
            notAllowedWord = ['а', 'но', 'да', 'тоже', 'зато', 'также', 'однако', 'когда', 'если', 'что', 'чтобы']
            location = 0
            
            for i in text:
                if i not in notAllowedWord:
                    worded = self.getEntryId('wordlist', 'word', i, 0)
                else:
                    worded = self.getEntryId('wordlist', 'word', i, isFiltered=1)
                locationWord = self.cursor.execute('insert into wordlocation (wordId, URLId, location) values (?, ?, ?)', (worded, urlid, location, ))
                location = location + 1
                self.conn.commit()
            

        

    def getTextOnly(self, soup):
        for script in soup(["script", "style"]):
            script.extract()    # rip it out

        # get text
        raw_text = soup.get_text()
        text = self.separateWords(raw_text)

        return text

    def separateWords(self, text):
        # break into lines and remove leading and trailing space on each
        lines = (line for line in text.split())
        # break multi-headlines into a line each
        # chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # # drop blank lines
        text = []
        for chunk in lines:
            if chunk:
                text.append(chunk)
        print(text)
        return text


    def getEntryId(self,table , field, value, isFiltered=0):
        query = f'select * from {table} WHERE {field} = ?'
        check = self.cursor.execute(query, (value, )).fetchone()
        if check:
            return check[0]
        else:
            query = f'insert into {table} ({field}, isFiltered) VALUES (?, ?)'
            self.cursor.execute(query, (value, isFiltered,))
            self.conn.commit()
            query = f'select * from {table} WHERE {field} = ?'
            check = self.cursor.execute(query, (value, )).fetchone()
            return check[0]

    def isIndexed(self, url):
        res = self.cursor.execute('SELECT * from URLList WHERE URL= ?', (url,)).fetchone()
        if res is not None:
            res2 = self.cursor.execute('SELECT * FROM wordLocation WHERE URLId = ?', (res[0],)).fetchone()
        if res is None or res2 is None:
            return False
        else:
            return True

    def addLinkRef(self, urlFrom, urlTo):
        # print("ADD LINK REF")
        # print(urlFrom, "---", urlTo)
        urlFrom_id = self.cursor.execute('SELECT row_id from URLList WHERE URL= ?', (urlFrom,)).fetchone()
        urlTo_id = self.cursor.execute('SELECT row_id from URLList WHERE URL= ?', (urlTo,)).fetchone()
        # print(urlFrom_id, "---", urlTo_id)
        if not self.cursor.execute('SELECT * from linkBetweenURL WHERE FromURL_id = ? AND ToURL_id = ?', (urlFrom_id[0], urlTo_id[0],)).fetchone():
            self.cursor.execute('INSERT INTO linkBetweenURL (FromURL_id, ToURL_id) VALUES(?,?)', (urlFrom_id[0], urlTo_id[0],))
            self.conn.commit()
        else:
            pass
        


    def crawl(self, urlList, maxDepth=1):
        print('Dive into page')
        for currDepth in range(maxDepth):
            print("YA TUT VOOBSHETO")
            print("currDepth: ", currDepth)
            tempList = []
            for url in urlList:
                html_doc = requests.get(url).text
                soup = BeautifulSoup(html_doc, 'html.parser')
                for script in soup(["script", "style"]):
                    script.extract()
                urlList.pop()
                for a in soup.find_all('a', href=True, ):
                    urlTo = ""
                    if a['href'][0:8] == 'https://' or a['href'][0:7] == 'http://':
                        urlTo = a['href']
                        tempList.append(a['href'])
                        
                        
                        if not self.isIndexed(url):
                            self.addURlList(url)
                    else:
                        urlTo = urljoin(url, a['href'])
                        tempList.append(urlTo)
                        
                        if self.isIndexed(url) == False:
                            self.addURlList(url)
                    if not self.isIndexed(urlTo):
                        self.addURlList(urlTo)
                    self.addLinkRef(urlFrom=url, urlTo=urlTo)
                    self.addToIndex(soup, url)
                    if a.contents:
                        linktext = a.text.split()
                        urlid = self.cursor.execute('select row_id from urllist where URL= ?', (url, )).fetchone()[0]
                        print(urlid)
                        words = []
                        if linktext is not None:
                            for text in linktext:
                                wordId = self.cursor.execute('select row_id from wordlist where word = ?', (text,)).fetchone()[0]
                                
                                if wordId is None:
                                    print('NONE FOUND: ', wordId, "--- TEXT: ", text)
                                words.append(wordId)
                            for word in words:
                                self.cursor.execute('insert into linkword (wordId, linkId) values (?, ?)', (word, urlid,))
                            self.conn.commit()
                                
                        else:
                            pass
                        print('LINK WORDS:', words)

                        # self.cursor.execute('insert into linkword (wordId, linkId) values (?, ?)', (wordId, linkId, ))
            urlList = tempList    
                # Получить список тегов а
                # Обработать тег
                # Проверить наличие href
                # Убрать пустые ссылки, вырезать якоря из ссылок
                # Добавить ссылку в список следующих на обход
                # извлечь из тэг а текст linkText
                # добавить в таблицу linkBetweenUrl БД ссылку с одной страницы на другую
                # Вызвать функцию класса для добавления содержимого в индекс


    def initDB(self):
    
        self.cursor.execute('create table if not EXISTS wordList  (row_id integer PRIMARY KEY, word TEXT,isFiltered INTEGER);')

        self.cursor.execute('create table if not EXISTS URLList  (row_id integer primary key, URL text);')
        self.cursor.execute('create table if not EXISTS wordLocation  (row_id integer primary key,wordId integer not null,URLId integer,location int,FOREIGN key (wordId) REFERENCES wordList(row_id),FOREIGN key (URLId) REFERENCES URLList(row_id));')
        self.cursor.execute('create table if not EXISTS linkBetweenURL  (row_id integer PRIMARY key,FromURL_id integer,ToURL_id integer,FOREIGN KEY (FromURL_id) REFERENCES URLList(row_id),FOREIGN KEY (ToURL_id) REFERENCES URLList(row_id));')
        self.cursor.execute('create table if not EXISTS linkWord  (row_id integer PRIMARY key,wordId int,linkId integer,FOREIGN key (wordId) REFERENCES wordList(row_id),FOREIGN key (linkId) REFERENCES linkBetweenURL(row_id));')
        self.conn.commit()
        





