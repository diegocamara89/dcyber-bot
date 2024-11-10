# database_manager.py
import sqlite3
from datetime import datetime
import time

class DatabaseManager:
    _instance = None
    DB_FILE = 'dcyber.db'
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def get_connection(self):
        """Obtém conexão com o banco de dados com retry"""
        max_attempts = 3
        attempt = 0
        while attempt < max_attempts:
            try:
                conn = sqlite3.connect(self.DB_FILE, timeout=20)
                return conn
            except sqlite3.OperationalError:
                attempt += 1
                time.sleep(1)
        raise Exception("Não foi possível conectar ao banco de dados após várias tentativas")
    
    def execute_query(self, query, params=None):
        """Executa uma query com tratamento de erros"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

# Criar instância global
db = DatabaseManager()