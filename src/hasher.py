import os
import sqlite3
import db

def process_files_for_hashes(root_path: str, db_path: str, files_list: list, paths_to_hash: list) -> dict:
    stats = {'calculated': 0, 'reused': 0, 'errors': 0}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Загружаем только пути и их текущие хэши
    cursor.execute("SELECT relative_path, hash FROM files")
    db_files = {row[0]: row[1] for row in cursor.fetchall()}
    
    updates = []
    
    for file in files_list:
        rel_path = file['relative_path']
        abs_path = os.path.join(root_path, rel_path)
        
        needs_rehash = True
        
        # Если файл НЕ был добавлен или изменен (его нет в paths_to_hash)
        if rel_path not in paths_to_hash:
            # И у него уже есть хэш в БД
            if db_files.get(rel_path):
                needs_rehash = False
                
        if needs_rehash:
            file_hash = db.get_file_hash(abs_path)
            if file_hash:
                updates.append((file_hash, rel_path))
                stats['calculated'] += 1
            else:
                stats['errors'] += 1
        else:
            stats['reused'] += 1
            
    if updates:
        cursor.executemany("UPDATE files SET hash = ? WHERE relative_path = ?", updates)
        conn.commit()
        
    conn.close()
    return stats
