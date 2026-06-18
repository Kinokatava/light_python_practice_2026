import os
import sqlite3
import db

def should_rehash(db_path: str, rel_path: str, current_size: int, current_mtime: float) -> bool:
    if not os.path.exists(db_path):
        return True
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT hash, size, modified_at FROM files WHERE relative_path = ?", 
        (rel_path,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return True
    
    db_size, db_mtime = row[1], row[2]
    if current_size != db_size or abs(current_mtime - db_mtime) > 1.0:
        return True
        
    return False

def process_files_for_hashes(root_path: str, db_path: str, files_list: list) -> dict:
    stats = {'calculated': 0, 'reused': 0, 'errors': 0}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT relative_path, hash, size, modified_at FROM files")
    db_files = {row[0]: {'hash': row[1], 'size': row[2], 'mtime': row[3]} for row in cursor.fetchall()}
    
    updates = []
    
    for file in files_list:
        rel_path = file['relative_path']
        abs_path = os.path.join(root_path, rel_path)
        
        db_info = db_files.get(rel_path)
        needs_rehash = True
        
        if db_info and db_info['hash']:
            if file['size'] == db_info['size'] and abs(file['modified_at'] - db_info['mtime']) <= 1.0:
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