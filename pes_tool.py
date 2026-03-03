# -*- coding: utf8 -*-
import sqlite3
import json
import os
import sys

DB_PATH = 'pes2017.db'
INVENTORY_PATH = 'my_inventory.json'

def load_inventory():
    if not os.path.exists(INVENTORY_PATH):
        # 初始化一份空的 inventory
        inv = {"owned_scouts": [], "owned_players": []}
        with open(INVENTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(inv, f, indent=4)
        return inv
    with open(INVENTORY_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_inventory(inv):
    with open(INVENTORY_PATH, 'w', encoding='utf-8') as f:
        json.dump(inv, f, indent=4, ensure_ascii=False)

def get_maps():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT scout_name, scout_id FROM scout_mapping')
    name_to_id = {row[0].lower(): row[1] for row in cursor.fetchall()}
    cursor.execute('SELECT scout_id, scout_name FROM scout_mapping')
    # 建立 ID 到名称的映射，注意 ID 冲突，我们可以把名称拼起来
    id_to_name = {}
    for sid, name in cursor.fetchall():
        if sid not in id_to_name:
            id_to_name[sid] = name
        elif name not in id_to_name[sid]:
            id_to_name[sid] += f" / {name}"
    conn.close()
    return name_to_id, id_to_name

def check_can_build():
    inv = load_inventory()
    name_to_id, id_to_name = get_maps()
    
    # 将手里持有的卡片名转换成 ID 集合
    owned_ids = set()
    for name in inv['owned_scouts']:
        if name.lower() in name_to_id:
            owned_ids.add(name_to_id[name.lower()])
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.name, p.rating, p.position, ps.scout1_id, ps.scout2_id, ps.scout3_id, ps.percent 
        FROM player_scouts ps
        JOIN players p ON ps.player_id = p.id
    ''')
    rows = cursor.fetchall()
    
    results = []
    for pid, pname, rating, pos, s1, s2, s3, percent in rows:
        needed = [s for s in [s1, s2, s3] if s != 0]
        if not needed: continue
        # 核心逻辑：是否所有需要的卡都在手里
        if all(sid in owned_ids for sid in needed):
            is_owned = str(pid) in [str(x) for x in inv['owned_players']]
            results.append((rating, pname, pos, needed, percent, is_owned))
            
    results.sort(key=lambda x: x[0], reverse=True)
    
    print("
" + "="*60)
    print("【基于现有库存：可合成球员推荐 (TOP 15)】")
    print("="*60)
    if not results:
        print("暂时没有 100% 可合成的球员方案。")
    else:
        for r in results[:15]:
            owned_tag = " (已拥有 ✅)" if r[5] else ""
            scout_str = " + ".join([id_to_name.get(sid, f"ID:{sid}") for sid in r[3]])
            print(f"[{r[0]}] {r[2]:4} | {r[1]:20} | {r[4]:3}% | 组合: {scout_str}{owned_tag}")
    conn.close()

def search_player(target):
    inv = load_inventory()
    name_to_id, id_to_name = get_maps()
    owned_ids = set()
    for name in inv['owned_scouts']:
        if name.lower() in name_to_id:
            owned_ids.add(name_to_id[name.lower()])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, rating FROM players WHERE name LIKE ?", (f'%{target}%',))
    players = cursor.fetchall()
    
    if not players:
        print(f"
找不到名为 '{target}' 的球员数据。请确保已运行爬虫抓取。")
        return

    for pid, pname, rating in players:
        print(f"
--- 目标分析: {pname} (评分: {rating}) ---")
        cursor.execute("SELECT scout1_id, scout2_id, scout3_id, percent FROM player_scouts WHERE player_id = ?", (pid,))
        schemes = cursor.fetchall()
        
        # 方案排序：缺少卡片数（少到多），几率（大到小）
        scored = []
        for s1, s2, s3, percent in schemes:
            needed = [s for s in [s1, s2, s3] if s != 0]
            missing = [id_to_name.get(sid, f"ID:{sid}") for sid in needed if sid not in owned_ids]
            scored.append((needed, missing, percent))
        scored.sort(key=lambda x: (len(x[1]), -x[2]))
        
        for needed, missing, percent in scored[:5]:
            n_str = " + ".join([id_to_name.get(sid, f"ID:{sid}") for sid in needed])
            if not missing:
                status = "【✅ 现成可用】"
            else:
                status = f"【❌ 缺少卡片: {', '.join(missing)}】"
            print(f" [{percent:3}%] {n_str:40} | {status}")
    conn.close()

def manage_inventory():
    while True:
        inv = load_inventory()
        print("
" + "-"*30)
        print(" 【PES 2017 库存管理】")
        print(" 1. 查看当前球探卡")
        print(" 2. 添加球探卡")
        print(" 3. 删除球探卡")
        print(" 4. 查看已有球员")
        print(" 5. 添加已有球员 (输入 ID)")
        print(" q. 退出")
        choice = input("
请选择: ").strip()
        
        if choice == '1':
            print("
当前球探卡:", ", ".join(inv['owned_scouts']) if inv['owned_scouts'] else "空")
        elif choice == '2':
            name = input("输入卡片名称 (如 LWF, FC BARCELONA, WALES): ").strip()
            if name:
                inv['owned_scouts'].append(name)
                save_inventory(inv)
                print("添加成功。")
        elif choice == '3':
            name = input("输入要删除的名称: ").strip()
            if name in inv['owned_scouts']:
                inv['owned_scouts'].remove(name)
                save_inventory(inv)
                print("已删除。")
        elif choice == '4':
            print("
已有球员 ID:", ", ".join([str(x) for x in inv['owned_players']]))
        elif choice == '5':
            pid = input("输入球员 ID: ").strip()
            if pid:
                inv['owned_players'].append(pid)
                save_inventory(inv)
                print("已添加。")
        elif choice == 'q':
            break

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'inv':
            manage_inventory()
        else:
            search_player(" ".join(sys.argv[1:]))
    else:
        print("正在分析当前库存能合出的最高评分球员...")
        check_can_build()
        print("
使用提示:")
        print(" 1. 搜球员合成方案: python pes_tool.py [球员名]")
        print(" 2. 管理库存: python pes_tool.py inv")
        print(" 3. 再次运行爬虫补充数据: python pes_spider.py")
