import psycopg2
from datetime import datetime
import time
import os

def get_db_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(DATABASE_URL)

def criar_tabela_estatisticas():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Tabela de contadores permanentes
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contadores_permanentes (
            id SERIAL PRIMARY KEY,
            tipo TEXT NOT NULL UNIQUE,
            total INTEGER DEFAULT 0,
            ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Tabela de ações por usuário
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS acoes_usuarios (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            tipo_acao TEXT NOT NULL,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Tabela de acessos
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_acessos (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            data_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo_acesso TEXT NOT NULL
        )
        ''')
        
        # Inicializar contadores se não existirem
        tipos = ['documentos', 'lembretes', 'contatos', 'usuarios', 'casos']
        for tipo in tipos:
            cursor.execute('''
            INSERT INTO contadores_permanentes (tipo, total)
            VALUES (%s, 0)
            ON CONFLICT (tipo) DO NOTHING
            ''', (tipo,))
        
        conn.commit()
    except Exception as e:
        print(f"Erro ao criar tabelas de estatísticas: {e}")
        raise e
    finally:
        conn.close()

def registrar_acao_usuario(user_id: int, tipo_acao: str):
    max_attempts = 3
    attempt = 0
    while attempt < max_attempts:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar se é a primeira ação do usuário
            cursor.execute('''
            SELECT COUNT(*) FROM acoes_usuarios WHERE user_id = %s
            ''', (user_id,))
            
            if cursor.fetchone()[0] == 0:
                incrementar_contador('usuarios')
            
            # Registrar a ação
            cursor.execute('''
            INSERT INTO acoes_usuarios (user_id, tipo_acao)
            VALUES (%s, %s)
            ''', (user_id, tipo_acao))
            
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            attempt += 1
            if attempt == max_attempts:
                print(f"Erro ao registrar ação após {max_attempts} tentativas: {e}")
                return False
            time.sleep(1)
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass
