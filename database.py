import psycopg2  
from datetime import datetime
import time

def get_db_connection():
    max_attempts = 3
    attempt = 0
    while attempt < max_attempts:
        try:
            conn = sqlite3.connect('dcyber.db', timeout=20)
            return conn
        except sqlite3.OperationalError:
            attempt += 1
            time.sleep(1)
    raise Exception("Não foi possível conectar ao banco de dados após várias tentativas")

def criar_tabela():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Recria a tabela de assinaturas com a estrutura correta
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
    conn.close()

def inserir_assinatura(user_id, username, documento, sequencia):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Atualizar username se já existir
        cursor.execute('''
            UPDATE assinaturas 
            SET username = %s
            WHERE user_id = %s AND username != %s
        ''', (username, user_id, username))
        
        # Inserir nova assinatura
        cursor.execute('''
            INSERT INTO assinaturas (user_id, username, documento, sequencia, ativo)
            VALUES (%s, %s, %s, %s, TRUE)
        ''', (user_id, username, documento, sequencia))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao inserir assinatura: {e}")
        return False
    finally:
        conn.close()

def criar_tabela_usuarios(admin_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Primeiro, vamos verificar se precisamos recriar a tabela
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        if cursor.fetchone() is not None:
            # Se a tabela existe, vamos removê-la
            cursor.execute('DROP TABLE IF EXISTS usuarios')
        
        # Criar a tabela com a nova estrutura
        cursor.execute('''
            CREATE TABLE usuarios (
                user_id INTEGER PRIMARY KEY,
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
        ''', (admin_id,))
        
        conn.commit()
    except Exception as e:
        print(f"Erro ao criar tabela de usuários: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

def recusar_usuario(user_id: int) -> bool:
    """Recusa um usuário pendente"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            DELETE FROM usuarios 
            WHERE user_id = %s AND nivel = 'pendente'
        ''', (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao recusar usuário: {e}")
        return False
    finally:
        conn.close()

def atualizar_nome_admin(admin_id: int) -> bool:
    """Atualiza o nome do admin para Diego"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE usuarios 
            SET nome = 'Diego', username = 'Diego'
            WHERE user_id = %s AND nivel = 'admin'
        ''', (admin_id,))
        conn.commit()
        print(f"Nome do admin atualizado com sucesso")  # Debug
        return True
    except Exception as e:
        print(f"Erro ao atualizar nome do admin: {e}")
        return False
    finally:
        conn.close()

def registrar_novo_usuario(user_id: int, nome: str, username: str = None) -> bool:
    """Registra um novo usuário como pendente"""
    print(f"Registrando novo usuário: ID={user_id}, Nome={nome}, Username={username}")  # Debug
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO usuarios (user_id, nome, username, nivel, ativo)
            VALUES (%s, %s, %s, 'pendente', FALSE)
        ''', (user_id, nome, username))
        conn.commit()
        print(f"Usuário registrado com sucesso")  # Debug
        return True
    except Exception as e:
        print(f"Erro ao registrar usuário: {e}")
        return False
    finally:
        conn.close()

def apagar_assinatura_por_sequencia(sequencia):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Primeiro, pegar as informações antes de apagar
        cursor.execute('''
        SELECT user_id, username, documento
        FROM assinaturas
        WHERE sequencia = %s AND ativo = TRUE
        ''', (sequencia,))
        resultado = cursor.fetchone()
        
        if resultado:
            user_id, username, documento = resultado
            
            # Marcar como inativo, mas não excluir o registro
            cursor.execute('''
            UPDATE assinaturas 
            SET ativo = FALSE 
            WHERE sequencia = %s
            ''', (sequencia,))
            
            conn.commit()
            return user_id, username, documento
            
        return None
    finally:
        conn.close()

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
        conn.close()

def gerar_sequencia():
    """Gera número sequencial apenas para assinaturas pendentes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Conta apenas assinaturas ativas
        cursor.execute('SELECT COUNT(*) FROM assinaturas WHERE ativo = TRUE')
        total_pendentes = cursor.fetchone()[0]
        
        # Se não houver pendentes, começa do 1
        if total_pendentes == 0:
            return 1
            
        # Caso contrário, usa o próximo número após o último pendente
        cursor.execute('SELECT MAX(sequencia) FROM assinaturas WHERE ativo = TRUE')
        ultimo_numero = cursor.fetchone()[0] or 0
        return ultimo_numero + 1
    except Exception as e:
        print(f"Erro ao gerar sequência: {e}")
        return 1
    finally:
        conn.close()

# Funções de verificação de nível
def is_admin(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT nivel FROM usuarios WHERE user_id = %s', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] == 'admin' if result else False

def is_dpc(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT nivel FROM usuarios WHERE user_id = %s', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] == 'dpc' if result else False

# Decorador para proteger funções admin
# Funções de gestão de usuários
def adicionar_usuario(user_id: int, nome: str, username: str = None, nivel: str = 'user') -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO usuarios (user_id, nome, username, nivel)
            VALUES (%s, %s, %s, %s)
        ''', (user_id, nome, username, nivel))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao adicionar usuário: {e}")
        return False
    finally:
        conn.close()

def alterar_nivel_usuario(user_id: int, novo_nivel: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE usuarios 
            SET nivel = %s, ativo = TRUE  -- Garantir que usuário fique ativo
            WHERE user_id = %s
        ''', (novo_nivel, user_id))
        conn.commit()
        
        # Verificar se a alteração foi bem sucedida
        cursor.execute('SELECT nivel, ativo FROM usuarios WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        print(f"Status após alteração - ID: {user_id}, Nível: {result[0]}, Ativo: {result[1]}")
        return True
    except Exception as e:
        print(f"Erro ao alterar nível do usuário: {e}")
        return False
    finally:
        conn.close()

def listar_usuarios() -> list:
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
        conn.close()

def criar_tabela_lembretes():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Apagar tabelas existentes
        cursor.execute('DROP TABLE IF EXISTS lembrete_destinatarios')
        cursor.execute('DROP TABLE IF EXISTS lembretes')
        
        # Criar tabela de lembretes
        cursor.execute('''
        CREATE TABLE lembretes (
            id SERIAL PRIMARY KEY,
            criador_id BIGINT NOT NULL,
            titulo TEXT NOT NULL,
            data DATE NOT NULL,
            hora TIME NOT NULL,
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Criar tabela de destinatários
        cursor.execute('''
        CREATE TABLE lembrete_destinatarios (
            id SERIAL PRIMARY KEY,
            lembrete_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            notificado BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (lembrete_id) REFERENCES lembretes (id),
            UNIQUE(lembrete_id, user_id)
        )
        ''')
        
        conn.commit()
    finally:
        conn.close()

def obter_id_dpc() -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT user_id FROM usuarios WHERE nivel = %s', ('dpc',))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

def obter_relatorio_atividades(data_inicio, data_fim):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print(f"Consultando período: {data_inicio} até {data_fim}")
        
        # Consulta para acessos
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
        
        # Consulta para assinaturas
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

        # Converter as datas para datetime
        acessos_processados = []
        for acesso in acessos:
            nome_usuario, nivel, data, primeiro_acesso, ultimo_acesso, total_acessos = acesso
            if isinstance(data, str):
                data = datetime.strptime(data, '%Y-%m-%d')
            if isinstance(primeiro_acesso, str):
                primeiro_acesso = datetime.strptime(primeiro_acesso, '%Y-%m-%d %H:%M:%S')
            if isinstance(ultimo_acesso, str):
                ultimo_acesso = datetime.strptime(ultimo_acesso, '%Y-%m-%d %H:%M:%S')
            acessos_processados.append((nome_usuario, nivel, data, primeiro_acesso, ultimo_acesso, total_acessos))

        assinaturas_processadas = []
        for assinatura in assinaturas:
            nome_usuario, data, total_assinaturas = assinatura
            if isinstance(data, str):
                data = datetime.strptime(data, '%Y-%m-%d')
            assinaturas_processadas.append((nome_usuario, data, total_assinaturas))

        return acessos_processados, assinaturas_processadas
        
    except Exception as e:
        print(f"Erro ao obter relatório: {e}")
        print(f"Data início: {data_inicio}, Data fim: {data_fim}")
        return [], []
    finally:
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
                INSERT OR IGNORE INTO contadores_permanentes (tipo, total)
                VALUES (%s, 0)
            ''', (tipo,))
        
        conn.commit()
    finally:
        conn.close()

def desativar_usuario(user_id: int) -> bool:
    """Desativa um usuário"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE usuarios 
            SET ativo = FALSE 
            WHERE user_id = %s
        ''', (user_id,))
        conn.commit()
        
        # Verificar se a atualização foi bem sucedida
        cursor.execute('SELECT ativo FROM usuarios WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        return not result[0] if result else False
    except Exception as e:
        print(f"Erro ao desativar usuário: {e}")
        return False
    finally:
        conn.close()

def registrar_acesso(user_id: int, tipo_acesso: str = 'login'):
    """Registrar um acesso do usuário"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO user_acessos (user_id, tipo_acesso)
            VALUES (%s, %s)
        ''', (user_id, tipo_acesso))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao registrar acesso: {e}")
        return False
    finally:
        conn.close()

def get_usuarios_cadastrados(excluir_user_id=None):
    """Obtém lista de usuários ativos com informações formatadas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT 
                user_id,
                CASE 
                    WHEN nome LIKE '% %' THEN substr(nome, 1, instr(nome, ' ')-1)
                    ELSE nome
                END as display_name
            FROM usuarios 
            WHERE user_id != %s 
            AND user_id IS NOT NULL
            AND ativo = TRUE
            AND nivel != 'pendente'
            ORDER BY nome
        ''', (excluir_user_id,))
        
        return cursor.fetchall()
    finally:
        conn.close()

def aprovar_usuario(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Atualiza tanto o nível quanto o status ativo
        cursor.execute('''
            UPDATE usuarios 
            SET nivel = 'user', ativo = TRUE 
            WHERE user_id = %s
        ''', (user_id,))
        conn.commit()
        
        # Verificar se a atualização foi bem sucedida
        cursor.execute('SELECT nivel, ativo FROM usuarios WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        print(f"Status após aprovação - ID: {user_id}, Nível: {result[0]}, Ativo: {result[1]}")  # Debug
        
        return True if result and result[1] else False
    except Exception as e:
        print(f"Erro ao aprovar usuário: {e}")
        return False
    finally:
        conn.close()

def listar_usuarios_pendentes() -> list:
    """Lista usuários com status pendente"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT user_id, nome, username, nivel, data_cadastro 
            FROM usuarios 
            WHERE nivel = 'pendente'
            ORDER BY data_cadastro
        ''')
        usuarios = cursor.fetchall()
        return [
            {
                'user_id': u[0],
                'nome': u[1],
                'username': u[2],
                'nivel': u[3],
                'data_cadastro': u[4]
            }
            for u in usuarios
        ]
    finally:
        conn.close()

def listar_usuarios_ativos() -> list:
    """Lista usuários ativos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT user_id, nome, username, nivel, data_cadastro 
            FROM usuarios 
            WHERE ativo = TRUE
            ORDER BY nivel, nome
        ''')
        usuarios = cursor.fetchall()
        return [
            {
                'user_id': u[0],
                'nome': u[1],
                'username': u[2],
                'nivel': u[3],
                'data_cadastro': u[4]
            }
            for u in usuarios
        ]
    finally:
        conn.close()

def get_user_display_info(user_id=None, username=None):
    """Função central para obter informações formatadas dos usuários"""
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
        conn.close()
