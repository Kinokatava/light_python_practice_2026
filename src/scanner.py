import os

def get_file_type(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext.lower() if ext else 'no_extension'

def _scan_recursive(current_path: str, root_path: str, allowed_exts: set, results: list) -> None:
    try:
        entries = os.listdir(current_path)
    except OSError:
        return

    for entry in entries:
        if entry.startswith('.') or entry == '__pycache__':
            continue
            
        abs_path = os.path.join(current_path, entry)
        
        try:
            if os.path.isdir(abs_path):
                _scan_recursive(abs_path, root_path, allowed_exts, results)
            else:
                file_type = get_file_type(entry)
                
                if allowed_exts and file_type not in allowed_exts:
                    continue
                    
                rel_path = os.path.relpath(abs_path, root_path)
                rel_path = rel_path.replace(os.sep, '/')

                try:
                    stat = os.stat(abs_path)
                    results.append({
                        'relative_path': rel_path,
                        'size': stat.st_size,
                        'modified_at': stat.st_mtime,
                        'file_type': file_type
                    })
                except OSError:
                    continue
        except OSError:
            continue

def scan_directory(root_path: str, allowed_exts: set = None) -> list:
    results = []
    _scan_recursive(root_path, root_path, allowed_exts, results)
    return results
