import sqlite3
import json
import os

DB_PATH = 'pes2017.db'
INVENTORY_PATH = 'my_inventory.json'

def load_inventory():
    if not os.path.exists(INVENTORY_PATH):
        return {"owned_scouts": [], "owned_players": []}
    with open(INVENTORY_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_scout_name_to_id_map():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT scout_name, scout_id FROM scout_mapping')
    mapping = {}
    for name, sid in cursor.fetchall():
        mapping[name.lower()] = sid
    conn.close()
    return mapping

def get_scout_id_to_name_map():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT scout_id, scout_name FROM scout_mapping')
    mapping = {}
    for sid, name in cursor.fetchall():
        # 由于 ID 可能在不同分类重复，我们这里简单映射，实际中 PESDB 的 ID 通常是全局唯一的
        mapping[sid] = name
    conn.close()
    return mapping

def check_what_i_can_build():
    inventory = load_inventory()
    name_to_id = get_scout_name_to_id_map()
    id_to_name = get_scout_id_to_name_map()
    
    owned_ids = set()
    for name in inventory['owned_scouts']:
        if name.lower() in name_to_id:
            owned_ids.add(name_to_id[name.lower()])
    
    owned_players = set(str(p) for p in inventory['owned_players'])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = '''
    SELECT p.id, p.name, p.rating, p.position, ps.scout1_id, ps.scout2_id, ps.scout3_id, ps.percent 
    FROM player_scouts ps
    JOIN players p ON ps.player_id = p.id
    '''
    cursor.execute(query)
    all_schemes = cursor.fetchall()
    
    results = []
    for pid, pname, rating, pos, s1, s2, s3, percent in all_schemes:
        needed = [s for s in [s1, s2, s3] if s != 0]
        if all(sid in owned_ids for sid in needed):
            is_owned = str(pid) in owned_players
            results.append((rating, pname, pos, needed, percent, is_owned))
            
    # 按评分排序
    results.sort(key=lambda x: x[0], reverse=True)
    
    print("\n" + "="*50)
    print("【基于当前球探卡：可合成球员推荐】")
    print("="*50)
    
    if not results:
        print("目前手里没有可 100% 合成的球员方案。")
    else:
        for r in results[:15]:
            stars = "★" * (r[0] // 20)
            owned_tag = " [已拥有]" if r[5] else ""
            scout_names = [id_to_name.get(sid, f"ID:{sid}") for sid in r[3]]
            print(f"[{r[0]}] {r[2]:4} | {r[1]:20} | 几率: {r[4]}% | 组合: {' + '.join(scout_names)}{owned_tag}")

def search_how_to_build(target_name):
    inventory = load_inventory()
    name_to_id = get_scout_name_to_id_map()
    id_to_name = get_scout_id_to_name_map()
    
    owned_ids = set()
    for name in inventory['owned_scouts']:
        if name.lower() in name_to_id:
            owned_ids.add(name_to_id[name.lower()])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, rating FROM players WHERE name LIKE ?", (f'%{target_name}%',))
    players = cursor.fetchall()
    
    if not players:
        print(f"\n数据库中未找到名为 '{target_name}' 的球员信息。")
        return

    for pid, pname, rating in players:
        print(f"\n分析目标: {pname} (评分: {rating})")
        cursor.execute("SELECT scout1_id, scout2_id, scout3_id, percent FROM player_scouts WHERE player_id = ?", (pid,))
        schemes = cursor.fetchall()
        
        # 评分：缺口卡片数（越少越好），几率（越高越好）
        scored = []
        for s1, s2, s3, percent in schemes:
            needed = [s for s in [s1, s2, s3] if s != 0]
            missing = [id_to_name.get(sid, f"ID:{sid}") for sid in needed if sid not in owned_ids]
            scored.append((needed, missing, percent))
            
        scored.sort(key=lambda x: (len(x[1]), -x[2]))
        
        for needed, missing, percent in scored[:5]:
            needed_names = [id_to_name.get(sid, f"ID:{sid}") for sid in needed]
            if not missing:
                status = "✅ 组合已齐全！"
            else:
                status = f"❌ 还差: {', '.join(missing)}"
            print(f"  [{percent:3}%] {' + '.join(needed_names):35} | {status}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        search_how_to_build(" ".join(sys.argv[1:]))
    else:
        check_what_i_can_build()
        print("\n提示: 运行 'python pes_logic.py [球员名]' 搜索特定球员合成路径。")
