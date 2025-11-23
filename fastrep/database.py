import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
from .models import LogEntry


class Database:
    """SQLite database manager for work logs."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to user's home directory
            home = Path.home()
            db_dir = home / '.fastrep'
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / 'fastrep.db'
        
        self.db_path = str(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_log(self, log: LogEntry) -> int:
        """Add a new log entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (project, description, date, created_at)
            VALUES (?, ?, ?, ?)
        ''', (
            log.project,
            log.description,
            log.date.strftime('%Y-%m-%d'),
            log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ))
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id
    
    def get_logs(self, start_date: Optional[datetime] = None, 
                 end_date: Optional[datetime] = None) -> List[LogEntry]:
        """Get logs within a date range."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT id, project, description, date, created_at FROM logs'
        params = []
        
        if start_date and end_date:
            query += ' WHERE date >= ? AND date <= ?'
            params = [
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            ]
        elif start_date:
            query += ' WHERE date >= ?'
            params = [start_date.strftime('%Y-%m-%d')]
        elif end_date:
            query += ' WHERE date <= ?'
            params = [end_date.strftime('%Y-%m-%d')]
        
        query += ' ORDER BY date DESC, created_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            logs.append(LogEntry(
                id=row[0],
                project=row[1],
                description=row[2],
                date=datetime.strptime(row[3], '%Y-%m-%d'),
                created_at=datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S')
            ))
        
        return logs
    
    def update_log(self, log_id: int, project: str, description: str, date: datetime) -> bool:
        """Update an existing log entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE logs 
            SET project = ?, description = ?, date = ?
            WHERE id = ?
        ''', (project, description, date.strftime('%Y-%m-%d'), log_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_log(self, log_id: int) -> bool:
        """Delete a log entry by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM logs WHERE id = ?', (log_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def clear_all(self):
        """Clear all log entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM logs')
        conn.commit()
        conn.close()
    
    def get_all_projects(self) -> List[str]:
        """Get list of all unique projects."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT project FROM logs ORDER BY project')
        projects = [row[0] for row in cursor.fetchall()]
        conn.close()
        return projects

    def get_setting(self, key: str, default: str = None) -> str:
        """Get a setting value by key."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        """Set a setting value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        ''', (key, str(value)))
        conn.commit()
        conn.close()
