import os
import psycopg2
from datetime import datetime
import time
from database_manager import db

def get_db_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

# Funções de criação de tabelas
def criar_tabela():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Recria a tabela de assinaturas
        cursor.execute('''DROP TABLE IF EXISTS assinaturas''')
        cursor.execute('''
            CREATE TABLE assinaturas (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username TEXT NOT NULL,
                documento TEXT NOT NULL,
                sequencia BIGINT NOT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def criar_tabela_usuarios(admin_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Criar a tabela com a nova estrutura
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                user_id BIGINT PRIMARY KEY,
                nome TEXT NOT NULL,
                username TEXT,
                nivel TEXT DEFAULT 'pendente',
                ativo BOOLEAN DEFAULT FALSE,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inserir admin padrão
        cursor.execute('''
            INSERT INTO usuarios (user_id, nome, username, nivel, ativo)
            VALUES (%s, 'Admin', 'admin', 'admin', TRUE)
            ON CONFLICT (user_id) DO UPDATE 
            SET nome = 'Admin', username = 'admin', nivel = 'admin', ativo = TRUE
        ''', (admin_id,))
        
        conn.commit()
    except Exception as e:
        print(f"Erro ao criar tabela de usuários: {e}")
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def criar_tabela_lembretes():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS lembretes (
            id SERIAL PRIMARY KEY,
            criador_id BIGINT NOT NULL,
            titulo TEXT NOT NULL,
            data DATE NOT NULL,
            hora TIME NOT NULL,
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS lembrete_destinatarios (
            id SERIAL PRIMARY KEY,
            lembrete_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            notificado BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (lembrete_id) REFERENCES lembretes (id) ON DELETE CASCADE,
            UNIQUE(lembrete_id, user_id)
        )
        ''')
        
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# Funções de usuários
def registrar_novo_usuario(user_id: int, nome: str, username: str = None) -> bool:
    print(f"Registrando novo usuário: ID={user_id}, Nome={nome}, Username={username}")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO usuarios (user_id, nome, username, nivel, ativo)
            VALUES (%s, %s, %s, 'pendente', FALSE)
            ON CONFLICT (user_id) DO NOTHING
            RETURNING user_id
        ''', (user_id, nome, username))
        result = cursor.fetchone()
        conn.commit()
        print(f"Usuário registrado com sucesso")
        return bool(result)
    except Exception as e:
        print(f"Erro ao registrar usuário: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def aprovar_usuario(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE usuarios 
            SET nivel = 'user', ativo = TRUE 
            WHERE user_id = %s
            RETURNING nivel, ativo
        ''', (user_id,))
        result = cursor.fetchone()
        conn.commit()
        print(f"Status após aprovação - ID: {user_id}, Nível: {result[0]}, Ativo: {result[1]}")
        return bool(result)
    except Exception as e:
        print(f"Erro ao aprovar usuário: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def recusar_usuario(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            DELETE FROM usuarios 
            WHERE user_id = %s AND nivel = 'pendente'
            RETURNING user_id
        ''', (user_id,))
        result = cursor.fetchone()
        conn.commit()
        return bool(result)
    except Exception as e:
        print(f"Erro ao recusar usuário: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Funções de assinaturas
def inserir_assinatura(user_id, username, documento, sequencia):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Atualizar username se já existir
        cursor.execute('''
            UPDATE assinaturas 
            SET username = %s
            WHERE user_id = %s AND username != %s
            RETURNING id
        ''', (username, user_id, username))
        
        # Inserir nova assinatura
        cursor.execute('''
            INSERT INTO assinaturas (user_id, username, documento, sequencia, ativo)
            VALUES (%s, %s, %s, %s, TRUE)
            RETURNING id
        ''', (user_id, username, documento, sequencia))
        
        result = cursor.fetchone()
        conn.commit()
        return bool(result)
    except Exception as e:
        print(f"Erro ao inserir assinatura: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def apagar_assinatura_por_sequencia(sequencia):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        SELECT user_id, username, documento
        FROM assinaturas
        WHERE sequencia = %s AND ativo = TRUE
        ''', (sequencia,))
        resultado = cursor.fetchone()
        
        if resultado:
            user_id, username, documento = resultado
            
            cursor.execute('''
            UPDATE assinaturas 
            SET ativo = FALSE 
            WHERE sequencia = %s
            RETURNING id
            ''', (sequencia,))
            
            conn.commit()
            return user_id, username, documento
            
        return None
    finally:
        cursor.close()
        conn.close()

# Funções de consulta
def consultar_assinaturas():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, user_id, username, documento, sequencia
            FROM assinaturas
            WHERE ativo = TRUE
            ORDER BY data_criacao DESC
        ''')
        return cursor.fetchall()
    except Exception as e:
        print(f"Erro ao consultar assinaturas: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def gerar_sequencia():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT COUNT(*) FROM assinaturas WHERE ativo = TRUE')
        total_pendentes = cursor.fetchone()[0]
        
        if total_pendentes == 0:
            return 1
            
        cursor.execute('SELECT MAX(sequencia) FROM assinaturas WHERE ativo = TRUE')
        ultimo_numero = cursor.fetchone()[0] or 0
        return ultimo_numero + 1
    except Exception as e:
        print(f"Erro ao gerar sequência: {e}")
        return 1
    finally:
        cursor.close()
        conn.close()

# Funções de verificação
def is_admin(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT nivel FROM usuarios WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        return result[0] == 'admin' if result else False
    finally:
        cursor.close()
        conn.close()

def is_dpc(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT nivel FROM usuarios WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        return result[0] == 'dpc' if result else False
    finally:
        cursor.close()
        conn.close()

def get_usuarios_cadastrados(excluir_user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT 
                user_id,
                CASE 
                    WHEN nome LIKE %s THEN split_part(nome, ' ', 1)
                    ELSE nome
                END as display_name
            FROM usuarios 
            WHERE user_id != %s 
            AND user_id IS NOT NULL
            AND ativo = TRUE
            AND nivel != 'pendente'
            ORDER BY nome
        ''', ('% %', excluir_user_id))
        
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_user_display_info(user_id=None, username=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if user_id:
            cursor.execute('''
                SELECT 
                    user_id,
                    username,
                    nome,
                    nivel,
                    ativo
                FROM usuarios 
                WHERE user_id = %s
            ''', (user_id,))
        elif username:
            cursor.execute('''
                SELECT 
                    user_id,
                    username,
                    nome,
                    nivel,
                    ativo
                FROM usuarios 
                WHERE username = %s
            ''', (username,))
        
        result = cursor.fetchone()
        if result:
            user_id, username, nome, nivel, ativo = result
            display_name = nome.split()[0] if nome and ' ' in nome else nome
            
            return {
                'user_id': user_id,
                'username': username,
                'nome_completo': nome,
                'display_name': display_name,
                'nivel': nivel,
                'ativo': ativo
            }
        return None
    finally:
        cursor.close()
        conn.close()

def obter_relatorio_atividades(data_inicio, data_fim):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print(f"Consultando período: {data_inicio} até {data_fim}")
        
        cursor.execute('''
            SELECT 
                COALESCE(u.nome, u.username) as nome_usuario,
                u.nivel,
                DATE(a.data_acesso) as data,
                MIN(a.data_acesso) as primeiro_acesso,
                MAX(a.data_acesso) as ultimo_acesso,
                COUNT(*) as total_acessos
            FROM user_acessos a
            JOIN usuarios u ON a.user_id = u.user_id
            WHERE a.data_acesso BETWEEN %s AND %s
            GROUP BY u.nome, u.username, u.nivel, DATE(a.data_acesso)
            ORDER BY DATE(a.data_acesso) DESC, nome_usuario
        ''', (data_inicio.strftime('%Y-%m-%d %H:%M:%S'), 
              data_fim.strftime('%Y-%m-%d %H:%M:%S')))
        
        acessos = cursor.fetchall()
        print(f"Acessos encontrados: {len(acessos)}")
        
        cursor.execute('''
            SELECT 
                COALESCE(u.nome, u.username) as nome_usuario,
                DATE(a.data_criacao) as data,
                COUNT(*) as total_assinaturas
            FROM assinaturas a
            JOIN usuarios u ON a.user_id = u.user_id
            WHERE a.data_criacao BETWEEN %s AND %s
            GROUP BY u.nome, u.username, DATE(a.data_criacao)
            ORDER BY DATE(a.data_criacao) DESC, nome_usuario
        ''', (data_inicio.strftime('%Y-%m-%d %H:%M:%S'), 
              data_fim.strftime('%Y-%m-%d %H:%M:%S')))
        
        assinaturas = cursor.fetchall()
        print(f"Assinaturas encontradas: {len(assinaturas)}")

        return acessos, assinaturas
        
    except Exception as e:
        print(f"Erro ao obter relatório: {e}")
        print(f"Data início: {data_inicio}, Data fim: {data_fim}")
        return [], []
    finally:
        cursor.close()
        conn.close()

def registrar_acesso(user_id: int, tipo_acesso: str = 'login'):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO user_acessos (user_id, tipo_acesso)
            VALUES (%s, %s)
            RETURNING id
        ''', (user_id, tipo_acesso))
        
        result = cursor.fetchone()
        conn.commit()
        return bool(result)
    except Exception as e:
        print(f"Erro ao registrar acesso: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def criar_tabela_acessos():
    """Criar tabela para registrar acessos dos usuários"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_acessos (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                data_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tipo_acesso TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES usuarios (user_id)
            )
        ''')
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def criar_todas_tabelas():
    """Cria todas as tabelas necessárias"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Tabela de acessos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_acessos (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                data_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tipo_acesso TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES usuarios (user_id)
            )
        ''')
        
        # Tabela de ações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS acoes_usuarios (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                tipo_acao TEXT NOT NULL,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES usuarios (user_id)
            )
        ''')
        
        # Tabela de contadores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contadores_permanentes (
                id SERIAL PRIMARY KEY,
                tipo TEXT NOT NULL UNIQUE,
                total INTEGER DEFAULT 0,
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inicializar contadores se não existirem
        tipos = ['documentos', 'lembretes', 'contatos', 'usuarios']
        for tipo in tipos:
            cursor.execute('''
                INSERT INTO contadores_permanentes (tipo, total)
                VALUES (%s, 0)
                ON CONFLICT (tipo) DO NOTHING
            ''', (tipo,))
        
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def listar_usuarios() -> list:
    """Lista todos os usuários"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT user_id, nome, username, nivel, data_cadastro 
            FROM usuarios 
            ORDER BY nivel, nome
        ''')
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def obter_id_dpc() -> int:
    """Obtém o ID do usuário DPC"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT user_id FROM usuarios WHERE nivel = %s', ('dpc',))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        conn.close()

def atualizar_nome_admin(admin_id: int) -> bool:
    """Atualiza o nome do admin"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE usuarios 
            SET nome = 'Diego', username = 'Diego'
            WHERE user_id = %s AND nivel = 'admin'
            RETURNING user_id
        ''', (admin_id,))
        result = cursor.fetchone()
        conn.commit()
        return bool(result)
    except Exception as e:
        print(f"Erro ao atualizar nome do admin: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
