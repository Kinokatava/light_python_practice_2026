import os
import time
import sqlite3
import db
import scanner

def _scan_backup_recursive(current_path: str, root_path: str, backup_files: dict, allowed_exts: set = None) -> None:
    try:
        entries = os.listdir(current_path)
    except OSError:
        return

    for entry in entries:
        if entry.startswith('.'):
            continue
            
        abs_path = os.path.join(current_path, entry)
        
        try:
            if os.path.isdir(abs_path):
                _scan_backup_recursive(abs_path, root_path, backup_files, allowed_exts)
            else:
                if allowed_exts:
                    file_type = scanner.get_file_type(entry)
                    if file_type not in allowed_exts:
                        continue

                rel_path = os.path.relpath(abs_path, root_path)
                try:
                    backup_files[rel_path] = {
                        'size': os.path.getsize(abs_path),
                        'abs_path': abs_path
                    }
                except OSError:
                    continue
        except OSError:
            continue

def compare_with_backup(db_path: str, source_path: str, backup_path: str, allowed_exts: set = None) -> tuple:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT relative_path, size, hash FROM files")
    source_files = {row[0]: {'size': row[1], 'hash': row[2]} for row in cursor.fetchall()}
    conn.close()
    
    backup_files = {}
    _scan_backup_recursive(backup_path, backup_path, backup_files, allowed_exts)
                
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
