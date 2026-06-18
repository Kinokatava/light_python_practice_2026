import os
import time
import sqlite3
import db

def compare_with_backup(db_path: str, source_path: str, backup_path: str) -> tuple:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT relative_path, size, hash FROM files")
    source_files = {row[0]: {'size': row[1], 'hash': row[2]} for row in cursor.fetchall()}
    conn.close()
    
    backup_files = {}
    for dirpath, dirnames, filenames in os.walk(backup_path):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for filename in filenames:
            if filename.startswith('.'):
                continue
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, backup_path)
            try:
                backup_files[rel_path] = {
                    'size': os.path.getsize(abs_path),
                    'abs_path': abs_path
                }
            except OSError:
                continue
                
    source_paths = set(source_files.keys())
    backup_paths = set(backup_files.keys())
    
    missing = list(source_paths - backup_paths)
    extra = list(backup_paths - source_paths)
    
    modified = []
    common = source_paths & backup_paths
    for path in common:
        src = source_files[path]
        bkp = backup_files[path]
        
        if src['size'] != bkp['size']:
            modified.append(path)
            continue
            
        if src['hash']:
            bkp_hash = db.get_file_hash(bkp['abs_path'])
            if src['hash'] != bkp_hash:
                modified.append(path)
                
    return missing, modified, extra

def save_backup_report(db_path: str, source_path: str, backup_path: str, 
                        missing: list, modified: list, extra: list) -> int:

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    check_date = time.time()
    cursor.execute("""
        INSERT INTO backup_checks 
        (check_date, source_path, backup_path, missing_count, modified_count, extra_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (check_date, source_path, backup_path, len(missing), len(modified), len(extra)))
    
    check_id = cursor.lastrowid
    
    diffs = []
    for p in missing: diffs.append((check_id, p, 'missing'))
    for p in modified: diffs.append((check_id, p, 'modified'))
    for p in extra: diffs.append((check_id, p, 'extra'))
    
    if diffs:
        cursor.executemany("""
            INSERT INTO backup_diffs (check_id, file_path, status)
            VALUES (?, ?, ?)
        """, diffs)
        
    conn.commit()
    conn.close()
    return check_id