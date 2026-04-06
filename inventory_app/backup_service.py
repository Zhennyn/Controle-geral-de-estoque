import shutil
from datetime import datetime
from pathlib import Path

from flask import current_app

from .models import db


def get_db_path():
    db_path = db.engine.url.database
    return Path(db_path)


def get_backup_dir():
    backup_dir = Path(current_app.instance_path) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_backup(tag="manual"):
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError("Banco de dados nao encontrado para backup.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"estoque_{tag}_{timestamp}.db"
    backup_file = get_backup_dir() / backup_name
    shutil.copy2(db_path, backup_file)
    return backup_file


def list_backups():
    return sorted(get_backup_dir().glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)


def restore_backup(filename):
    backup_file = get_backup_dir() / filename
    if not backup_file.exists():
        raise FileNotFoundError("Arquivo de backup nao encontrado.")

    db_path = get_db_path()
    db.session.remove()
    db.engine.dispose()
    shutil.copy2(backup_file, db_path)


def ensure_daily_backup():
    today = datetime.now().strftime("%Y%m%d")
    backups = list_backups()
    if any(today in b.name for b in backups):
        return None

    db_path = get_db_path()
    if db_path.exists():
        return create_backup(tag="auto")
    return None
