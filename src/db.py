import os
import sqlite3
import hashlib

def init_db(db_path: str) -> None:
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    create_table_query = """
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        relative_path TEXT UNIQUE NOT NULL,
        size INTEGER,
        modified_at REAL,
        file_type TEXT,
        hash TEXT
    );
    """
    
    cursor.execute(create_table_query)
    
    # Таблица для хранения факта и статистики проверок
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS backup_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_date REAL NOT NULL,
        source_path TEXT NOT NULL,
        backup_path TEXT NOT NULL,
        missing_count INTEGER DEFAULT 0,
        modified_count INTEGER DEFAULT 0,
        extra_count INTEGER DEFAULT 0
    );
    """)
    
    # Таблица для хранения конкретных расхождений (история)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS backup_diffs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        status TEXT NOT NULL, -- 'missing', 'modified', 'extra'
        FOREIGN KEY (check_id) REFERENCES backup_checks (id)
    );
    """)
    
    conn.commit()
    conn.close()

def sync_db(db_path: str, scanned_files: list) -> tuple:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT relative_path FROM files")
    old_paths = {row[0] for row in cursor.fetchall()}
    
    new_paths = {f['relative_path'] for f in scanned_files}
    
    paths_to_delete = old_paths - new_paths

    added = 0
    updated = 0

    for file in scanned_files:
        cursor.execute("SELECT id FROM files WHERE relative_path = ?", (file['relative_path'],))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE files 
                SET size=?, modified_at=?, file_type=? 
                WHERE relative_path=?
            """, (file['size'], file['modified_at'], file['file_type'], file['relative_path']))
            updated += 1
        else:
            cursor.execute("""
                INSERT INTO files (relative_path, size, modified_at, file_type)
                VALUES (?, ?, ?, ?)
            """, (file['relative_path'], file['size'], file['modified_at'], file['file_type']))
            added += 1

    deleted = 0
    if paths_to_delete:
        cursor.executemany(
            "DELETE FROM files WHERE relative_path = ?", 
            [(p,) for p in paths_to_delete]
        )
        deleted = cursor.rowcount

    conn.commit()
    conn.close()
    
    return added, updated, deleted


def get_file_hash(file_path: str, algorithm: str = 'md5', chunk_size: int = 8192) -> str:
    hasher = hashlib.new(algorithm)
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, IOError):
        return None

def find_duplicates(db_path: str) -> list:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
    SELECT relative_path, hash 
    FROM files 
    WHERE hash IS NOT NULL 
    GROUP BY hash 
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
    """
    
    cursor.execute(query)
    duplicate_hashes = [row[1] for row in cursor.fetchall()]
    
    duplicates = []
    
    for dup_hash in duplicate_hashes:
        cursor.execute(
            "SELECT relative_path FROM files WHERE hash = ? ORDER BY relative_path", 
            (dup_hash,)
        )
        group = [row[0] for row in cursor.fetchall()]
        if len(group) > 1:
            duplicates.append(group)
    
    conn.close()
    return duplicates

def update_file_hash(db_path: str, relative_path: str, file_hash: str) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE files SET hash = ? WHERE relative_path = ?",
        (file_hash, relative_path)
    )
    conn.commit()
    conn.close()