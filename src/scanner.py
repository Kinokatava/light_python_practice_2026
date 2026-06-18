import os

def get_file_type(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext.lower() if ext else 'no_extension'

def scan_directory(root_path: str, allowed_exts: set = None) -> list:
    results = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
        
        for filename in filenames:
            if filename.startswith('.'):
                continue
                
            file_type = get_file_type(filename)
            
            if allowed_exts and file_type not in allowed_exts:
                continue
                
            abs_path = os.path.join(dirpath, filename)
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
                
    return results