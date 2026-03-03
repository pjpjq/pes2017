import urllib.request
from bs4 import BeautifulSoup
import sqlite3
import re
from urllib.parse import urljoin, urlparse, parse_qs

DB_PATH = 'pes2017.db'

def get_mapping_from_url(url, conn):
    print(f"Fetching mappings from {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(urllib.request.urlopen(req).read(), 'lxml')
    cursor = conn.cursor()
    
    selects = soup.find_all('select')
    for s in selects:
        s_name = s.get('name')
        if not s_name or not s_name.startswith('scout_'): continue
        for opt in s.find_all('option'):
            v = opt.get('value')
            t = opt.string
            if v and v != '0' and t:
                # 提取最具体的名称，比如 "Europe / SPAIN" 提取 "SPAIN"
                clean_t = t.split('/')[-1].strip()
                cursor.execute('INSERT OR REPLACE INTO scout_mapping VALUES (?, ?, ?)', (s_name, int(v), clean_t))
    conn.commit()

if __name__ == '__main__':
    conn = sqlite3.connect(DB_PATH)
    # 分别从不同筛选页面提取映射关系
    urls = [
        'http://pesdb.net/pes2017/',
        'http://pesdb.net/pes2017/?scout_league=7', # Spanish League
        'http://pesdb.net/pes2017/?scout_league=2', # English League
        'http://pesdb.net/pes2017/?scout_league=1', # Free Agent
    ]
    for u in urls:
        get_mapping_from_url(u, conn)
    conn.close()
