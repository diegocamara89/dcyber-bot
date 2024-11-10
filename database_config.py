import os
import psycopg2
from psycopg2.extras import DictCursor
from urllib.parse import urlparse

def get_db_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL:
        # Heroku
        url = urlparse(DATABASE_URL)
        connection = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
    else:
        # Local
        connection = psycopg2.connect(
            database="dcyber_bot",
            user="postgres",
            password=os.getenv('DB_PASSWORD'),
            host="localhost",
            port="5432"
        )
    
    connection.autocommit = True
    return connection

def init_db():
    """Inicializa todas as tabelas do banco"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Usuários
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            user_id BIGINT PRIMARY KEY,
            nome TEXT NOT NULL,
            username TEXT,
            nivel TEXT DEFAULT 'pendente',
            ativo BOOLEAN DEFAULT FALSE,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Assinaturas
    cur.execute('''
        CREATE TABLE IF NOT EXISTS assinaturas (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            username TEXT NOT NULL,
            documento TEXT NOT NULL,
            sequencia INTEGER NOT NULL,
            ativo BOOLEAN DEFAULT TRUE,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
        )
    ''')
    
    # Casos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS casos (
            id SERIAL PRIMARY KEY,
            titulo TEXT NOT NULL,
            observacoes TEXT,
            status TEXT NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo BOOLEAN DEFAULT TRUE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS caso_responsaveis (
            id SERIAL PRIMARY KEY,
            caso_id INTEGER NOT NULL,
            user_id BIGINT NOT NULL,
            FOREIGN KEY (caso_id) REFERENCES casos(id),
            FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
        )
    ''')
    
    # Estatísticas
    cur.execute('''
        CREATE TABLE IF NOT EXISTS contadores_permanentes (
            id SERIAL PRIMARY KEY,
            tipo TEXT NOT NULL UNIQUE,
            total INTEGER DEFAULT 0,
            ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Acessos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_acessos (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            data_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo_acesso TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()