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
        cursor.close()
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
            SET total = total + %s, 
                ultima_atualizacao = CURRENT_TIMESTAMP 
            WHERE tipo = %s
            RETURNING id
            ''', (quantidade, tipo))
            result = cursor.fetchone()
            conn.commit()
            return bool(result)
        except Exception as e:
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
    timezone = pytz.timezone('America/Sao_Paulo')
    
    while attempt < max_attempts:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Configurar timezone
            cursor.execute("SET timezone TO 'America/Sao_Paulo'")
            
            # Verificar se é a primeira ação do usuário
            cursor.execute('''
            SELECT COUNT(*) FROM acoes_usuarios WHERE user_id = %s
            ''', (user_id,))
            
            if cursor.fetchone()[0] == 0:
                incrementar_contador('usuarios')
            
            # Registrar a ação com timezone
            agora = datetime.now(timezone)
            cursor.execute('''
            INSERT INTO acoes_usuarios (user_id, tipo_acao, data_hora)
            VALUES (%s, %s, %s)
            RETURNING id
            ''', (user_id, tipo_acao, agora))
            
            result = cursor.fetchone()
            conn.commit()
            return bool(result)
        except Exception as e:
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

    return False

def obter_estatisticas():
    """Obtém estatísticas gerais do sistema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT tipo, total FROM contadores_permanentes')
        return dict(cursor.fetchall())
    finally:
        cursor.close()
        conn.close()
