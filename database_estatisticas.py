# database_estatisticas.py
import sqlite3
from datetime import datetime
import time

def get_db_connection():
    max_attempts = 3
    attempt = 0
    while attempt < max_attempts:
        try:
            conn = sqlite3.connect('dcyber_stats.db', timeout=20)
            return conn
        except sqlite3.OperationalError:
            attempt += 1
            time.sleep(1)
    raise Exception("Não foi possível conectar ao banco de dados após várias tentativas")

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
            INSERT OR IGNORE INTO contadores_permanentes (tipo, total)
            VALUES (%s, 0)
            ''', (tipo,))
        
        conn.commit()
    except Exception as e:
        print(f"Erro ao criar tabelas de estatísticas: {e}")
        raise e
    finally:
        conn.close()

def incrementar_contador(tipo: str, quantidade: int = 1):
    max_attempts = 3
    attempt = 0
    while attempt < max_attempts:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE contadores_permanentes 
            SET total = total + %s, ultima_atualizacao = CURRENT_TIMESTAMP 
            WHERE tipo = %s
            ''', (quantidade, tipo))
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            attempt += 1
            if attempt == max_attempts:
                print(f"Erro ao incrementar contador após {max_attempts} tentativas: {e}")
                return False
            time.sleep(1)
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

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