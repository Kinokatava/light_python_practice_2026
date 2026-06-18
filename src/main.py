import argparse
import sys
import os
import db
import scanner
import hasher
import backup

def main():
    parser = argparse.ArgumentParser(
        description="Консольный индексатор с поиском дубликатов и проверкой бэкапов."
    )
    
    parser.add_argument("path", type=str, help="Путь к папке-источнику")
    parser.add_argument("--ext", nargs="*", help="Фильтр по расширениям")
    parser.add_argument("--find-dupes", action="store_true", help="Найти дубликаты")
    
    parser.add_argument(
        "--backup",
        type=str,
        help="Путь к папке с резервной копией для сравнения с источником"
    )
    
    args = parser.parse_args()
    target_path = os.path.abspath(args.path)
    
    if not os.path.isdir(target_path):
        print(f"Ошибка: '{args.path}' не является папкой.")
        sys.exit(1)
        
    print(f"Источник: '{target_path}'")
    
    allowed_exts = None
    if args.ext:
        allowed_exts = set()
        for e in args.ext:
            ext = e.lower()
            if not ext.startswith('.'): ext = '.' + ext
            allowed_exts.add(ext)

    # Инициализация БД
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, 'data', 'index.db')
    db.init_db(db_path)

    # 1. Сканирование и синхронизация
    scanned_files = scanner.scan_directory(target_path, allowed_exts)
    added, updated, deleted = db.sync_db(db_path, scanned_files)
    print(f"Индекс источника обновлен: +{added} ~{updated} -{deleted}")
    
    # 2. Хеширование
    if args.find_dupes or args.backup:
        print("\nВычисление хэшей источника...")
        hash_stats = hasher.process_files_for_hashes(target_path, db_path, scanned_files)
        print(f"Хэши: посчитано: {hash_stats['calculated']}, взято из кэша: {hash_stats['reused']}")

    # 3. поиск дублей
    if args.find_dupes:
        print("\nПоиск дубликатов...")
        duplicates = db.find_duplicates(db_path)
        if not duplicates:
            print("Дубликаты не найдены.")
        else:
            print(f"Найдено групп дубликатов: {len(duplicates)}")
            for i, group in enumerate(duplicates[:3], 1):
                print(f"Группа #{i}: {group}")

    # 4. проверка резерв копии
    if args.backup:
        backup_path = os.path.abspath(args.backup)
        if not os.path.isdir(backup_path):
            print(f"Ошибка: Путь бэкапа '{args.backup}' не существует.")
            sys.exit(1)
            
        print(f"\nСравнение с резервной копией: '{backup_path}'...")
        
        missing, modified, extra = backup.compare_with_backup(db_path, target_path, backup_path)
        check_id = backup.save_backup_report(db_path, target_path, backup_path, missing, modified, extra)
        
        print(f"ID отчета: {check_id}")
        print(f"Источник: {target_path}")
        print(f"Бэкап:    {backup_path}")
        
        print(f"Отсутствуют в бэкапе (Missing): {len(missing)}")
        for p in missing[:5]: print(f"   • {p}")
        if len(missing) > 5: print(f"   ... и еще {len(missing)-5}")
        
        print(f"Изменены (Modified):           {len(modified)}")
        for p in modified[:5]: print(f"   • {p}")
        if len(modified) > 5: print(f"   ... и еще {len(modified)-5}")
        
        print(f"Лишние в бэкапе (Extra):       {len(extra)}")
        for p in extra[:5]: print(f"   • {p}")
        if len(extra) > 5: print(f"   ... и еще {len(extra)-5}")

if __name__ == "__main__":
    main()