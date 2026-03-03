import urllib.request
from bs4 import BeautifulSoup
import sqlite3
import re
from urllib.parse import urljoin, urlparse, parse_qs
from time import sleep

DB_PATH = 'pes2017.db'
BASE_URL = 'http://pesdb.net/pes2017/'

def parse_player_page(url, conn):
    try:
        player_id = int(parse_qs(urlparse(url).query)['id'][0])
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        soup = BeautifulSoup(response.read(), 'lxml')
        
        name = soup.title.string.replace(' - pesdb.net', '').strip()
        rating = int(soup.find(id='a23').string)
        position_tag = soup.find('th', string='Position:')
        position = position_tag.find_next_sibling('td').string if position_tag else 'Unknown'
            
        print(f"Parsing Player: {name} ({rating})")
        
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO players VALUES (?,?,?,?)', (player_id, name, rating, position))
        
        rows = soup.find_all('tr', class_='scout_row')
        for row in rows:
            data_free = int(row.get('data-free', 0))
            data_percent = int(row.get('data-percent', 0))
            
            # 这里是关键：提取球探 ID 和 名称
            # 示例：<a href="../?scout_stars=5&scout_area=1&scout_nationality=64">WALES</a>
            scout_links = row.find_all('a')
            ids = [0, 0, 0]
            for idx, link in enumerate(scout_links):
                href = link['href']
                s_name = link.string
                qs = parse_qs(urlparse(href).query)
                
                # 提取除了 scout_stars 以外的第一个 scout_ 参数作为 ID
                for k, v in qs.items():
                    if k != 'scout_stars' and k.startswith('scout_'):
                        s_id = int(v[0])
                        if idx < 3: ids[idx] = s_id
                        # 更新映射表
                        cursor.execute('INSERT OR REPLACE INTO scout_mapping (scout_type, scout_id, scout_name) VALUES (?, ?, ?)',
                                     (k, s_id, s_name))
                        break
            
            cursor.execute('INSERT INTO player_scouts VALUES (?,?,?,?,?,?)', 
                         (player_id, ids[0], ids[1], ids[2], data_percent, data_free))
        conn.commit()
    except Exception as e:
        print(f"Error parsing player {url}: {e}")

def main():
    conn = sqlite3.connect(DB_PATH)
    # 重新抓取 100% 几率的前几页，这次带上 ID 学习功能
    for page in range(1, 3):
        print(f"--- Fetching Page {page} ---")
        list_url = f"{BASE_URL}?scout_percent=100&page={page}"
        req = urllib.request.Request(list_url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(urllib.request.urlopen(req).read(), 'lxml')
        player_urls = [urljoin(BASE_URL, a['href']) for a in soup.find_all('a', href=re.compile(r'\?id=\d+'))]
        
        for p_url in list(set(player_urls)):
            parse_player_page(p_url, conn)
            sleep(2)
            
    conn.close()

if __name__ == '__main__':
    main()
