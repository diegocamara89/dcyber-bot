import psycopg2
from datetime import datetime
import time
import os
from urllib.parse import urlparse

class DatabaseManager:
    _instance = None
    
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
                DATABASE_URL = os.getenv('DATABASE_URL')
                if DATABASE_URL.startswith("postgres://"):
                    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
                conn = psycopg2.connect(DATABASE_URL)
                conn.autocommit = True
                return conn
            except psycopg2.OperationalError:
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
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

# Criar instância global
db = DatabaseManager()
