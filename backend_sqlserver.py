import os
import urllib.parse as up
import psycopg2
from copy import copy
from threading import Lock

from face_detaction.dnschef import start_dns_server
from face_detaction.gad import start_cam_therad
from http_server.http_test import start_http_server

class BackEndApp(object):

    def __init__(self):
        super().__init__()
        self.lock = Lock()
        self.dns_db = None
        self.database = Database()
        self.started_once = False
        start_http_server(80)
        start_http_server(443)

    def start(self):
        blocked_domains = self.database.build_blocked_dict()
        if  not self.started_once:
            self.started_once=True
            self.dns_db = start_dns_server("127.0.0.2",blocked_urls=blocked_domains,lock_dns=self.lock)
            start_cam_therad(dns_db=self.dns_db,dns_lock=self.lock,blocked_urls=blocked_domains)
        else:
            self.lock.acquire()
            self.dns_db=blocked_domains
            self.lock.release()

        
    def stop(self):
        self.lock.acquire()
        self.dns_db = dict()
        self.lock.release()




def start_app(blocked_domains):

    # we can update this from any place and it will affect all apps
    dns_lock = Lock()  # shared lock between cam and dns apps
    dns_db = start_dns_server("127.0.0.1",blocked_urls=blocked_domains,lock_dns=dns_lock)
    # dns db is the dict that both apps will use
    start_cam_therad(dns_db=dns_db,dns_lock=dns_lock,blocked_urls=blocked_domains)


class Database():

    def __init__(self):
        self.connection = psycopg2.connect(database="data-base name",user="data-base user",password="password",host="host",port="5432")
        self.cursor = self.connection.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS blacklist (url TEXT)")
        self.connection.commit()
        self.bloced_dict = dict()

    def insert(self,url):
        res=self.search(url)
        if res==[]:
            self.cursor.execute("INSERT INTO blacklist VALUES (%s)",(url,))
            self.connection.commit()
        else:
            pass

    def view(self):
        self.cursor.execute("SELECT * FROM blacklist")
        self.selfrows = self.cursor.fetchall()
        return self.selfrows

    def search(self,url=""):
        self.cursor.execute("SELECT * FROM blacklist WHERE url=%s ",(url,))
        rows = self.cursor.fetchall()
        return rows
        
    def delete(self,url): 
        print(url)
        try:
            self.cursor.execute("DELETE FROM blacklist WHERE url=%s",(url,))
            self.connection.commit()
        except:
            print("eror")

    def clear_tables(self):
        self.cursor.execute("TRUNCATE TABLE blacklist")
        self.connection.commit()

    def __del__(self):
       if self:
           self.cursor.close()
    
    def build_blocked_dict(self):
        self.view()
        self.blocked_dict = dict()
        if not self.selfrows:
            return
        for url in self.selfrows:
            
            fixed_url = url[0].split("//")[-1]
            self.bloced_dict[fixed_url] = "127.0.0.1"
        return copy(self.bloced_dict)

