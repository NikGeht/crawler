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
                i.lower()
                if i not in notAllowedWord:
                    worded = self.getEntryId('wordlist', 'word', i, 0)
                else:
                    worded = self.getEntryId('wordlist', 'word', i, isFiltered=1)
                locationWord = self.cursor.execute('insert into wordlocation (wordId, URLId, location) values (?, ?, ?)', (worded, urlid, location, ))
                location = location + 1
                self.conn.commit()
            
            linktext = self.cursor.execute(f'select linktext from linkbetweenurl where fromurl_id={urlid}').fetchall()
            for rows in linktext:
                # print("LINKTEXT ----> ", linktext)
                for text in rows:
                    for i in text.split():
                        wordId = self.cursor.execute('select row_id from wordlist where word = ?', (i,)).fetchone()   
                        print("WORDID ----> ", wordId) 
                        if wordId is None:
                            print('NONE FOUND: ', wordId, "--- TEXT: ", i)
                        else:
                            self.cursor.execute('insert into linkword (wordId, linkId) values (?, ?)', (wordId[0], urlid,))
                            self.conn.commit()
            

        

    def getTextOnly(self, soup: BeautifulSoup):
        text = soup.find_all(text=True)
        text_out = ''
        blacklist = [
            '[document]',
            'noscript',
            'header',
            'html',
            'meta',
            'head',
            'input',
            'script',
            'style',
        ]

        for t in text:
            if t.parent.name not in blacklist:
                text_out += '{} '.format(t)
        text_out = self.separateWords(text_out)
        return text_out

    def separateWords(self, text):
        # break into lines and remove leading and trailing space on each
        lines = (line for line in text.split())
        # break multi-headlines into a line each
        # chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # # drop blank lines
        text = []
        for chunk in lines:
            if chunk:
                text.append(chunk.lower())
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

    def addLinkRef(self, urlFrom, urlTo, linktext: str):
        # print("ADD LINK REF")
        # print(urlFrom, "---", urlTo)
        urlFrom_id = self.cursor.execute('SELECT row_id from URLList WHERE URL= ?', (urlFrom,)).fetchone()
        urlTo_id = self.cursor.execute('SELECT row_id from URLList WHERE URL= ?', (urlTo,)).fetchone()
        # print(urlFrom_id, "---", urlTo_id)
        if not self.cursor.execute('SELECT * from linkBetweenURL WHERE FromURL_id = ? AND ToURL_id = ?', (urlFrom_id[0], urlTo_id[0],)).fetchone():
            self.cursor.execute('INSERT INTO linkBetweenURL (FromURL_id, ToURL_id, linktext) VALUES(?,?,?)', (urlFrom_id[0], urlTo_id[0], linktext,))
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
                html_page = requests.get(url).content
                soup = BeautifulSoup(html_page, 'html.parser')
                urlList.pop()
                print(url)
                for a in soup.find_all('a', href=True, ):
                    urlTo = ""
                    if a['href'][0:8] == 'https://' or a['href'][0:7] == 'http://':
                        urlTo = a['href']
                        tempList.append(a['href'])
                        
                    else:
                        urlTo = urljoin(url, a['href'])
                        tempList.append(urlTo)
                    
                    check_url = self.cursor.execute('select row_id from urllist where URL= ?', (url, )).fetchone()
                    check_urlTo = self.cursor.execute('select row_id from urllist where URL= ?', (urlTo, )).fetchone()
                    linktext = str(a.text.lower()).split()
                    linktext = ' '.join(linktext)
                    if linktext != ' ' or linktext != '':
                        if check_url is None:
                            self.addURlList(url)
                        if check_urlTo is None:
                            self.addURlList(urlTo)
                        
                        self.addLinkRef(urlFrom=url, urlTo=urlTo, linktext=linktext)
            

                self.addToIndex(soup, url)
            urlList = tempList
                    # words = []
                    # linktext = a.text.lower()
                    # link_texts = linktext.split()
                    # urlid = self.cursor.execute('select row_id from urllist where URL= ?', (url, )).fetchone()[0]
                    # if linktext is not None:
                    #     for text in link_texts:
                    #         wordId = self.cursor.execute('select row_id from wordlist where word = ?', (text,)).fetchone()
                            
                    #         if wordId is None:
                    #             print('NONE FOUND: ', wordId, "--- TEXT: ", text)
                    #         else:
                    #             words.append(wordId[0])
                    #     for word in words:
                    #         self.cursor.execute('insert into linkword (wordId, linkId) values (?, ?)', (word, urlid,))
                    #         self.conn.commit()
                            
                    # else:
                    #     pass
                    # print('LINK WORDS:', words)
                        
                    
                    
                    
                    

                        # self.cursor.execute('insert into linkword (wordId, linkId) values (?, ?)', (wordId, linkId, ))
                
               
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
        self.cursor.execute('create table if not EXISTS linkBetweenURL  (row_id integer PRIMARY key,FromURL_id integer,ToURL_id integer, linktext text, FOREIGN KEY (FromURL_id) REFERENCES URLList(row_id),FOREIGN KEY (ToURL_id) REFERENCES URLList(row_id));')
        self.cursor.execute('create table if not EXISTS linkWord  (row_id integer PRIMARY key,wordId int,linkId integer,FOREIGN key (wordId) REFERENCES wordList(row_id),FOREIGN key (linkId) REFERENCES linkBetweenURL(row_id));')
        self.conn.commit()
        





