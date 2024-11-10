# database_contatos.py
from database_manager import db

def criar_tabela_contatos():
    """Cria tabela de contatos"""
    query = '''
    CREATE TABLE IF NOT EXISTS contatos (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        nome TEXT NOT NULL,
        contato TEXT,
        observacoes TEXT,
        ativo BOOLEAN DEFAULT TRUE,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES usuarios (user_id)
    )
    '''
    
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        conn.commit()
    finally:
        conn.close()

def adicionar_contato_db(user_id, nome, contato, observacoes=None):
    """Adiciona um novo contato"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO contatos (user_id, nome, contato, observacoes)
            VALUES (%s, %s, %s, %s)
        ''', (user_id, nome, contato, observacoes))
        conn.commit()
        return cursor.lastrowid  # Retorna o ID do contato inserido
    except Exception as e:
        print(f"Erro ao adicionar contato: {e}")
        return None
    finally:
        conn.close()

def consultar_contatos_db(user_id=None, busca=None):
    """Consulta contatos com filtros"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        query = '''
            SELECT id, nome, contato, observacoes, criado_em
            FROM contatos
            WHERE ativo = TRUE
        '''
        params = []
        
        if user_id:
            query += ' AND user_id = %s'
            params.append(user_id)
        
        if busca:
            query += ' AND (nome LIKE %s OR contato LIKE %s OR observacoes LIKE %s)'
            busca_param = f'%{busca}%'
            params.extend([busca_param, busca_param, busca_param])
        
        query += ' ORDER BY nome'
        
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        conn.close()

def pesquisar_contatos_db(user_id: int, termo: str):
    """Pesquisa contatos com base em um termo"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        SELECT id, nome, contato, observacoes, criado_em
        FROM contatos
        WHERE user_id = %s 
        AND ativo = TRUE
        AND (nome LIKE %s OR contato LIKE %s OR observacoes LIKE %s)
        ORDER BY nome ASC
        ''', (user_id, f'%{termo}%', f'%{termo}%', f'%{termo}%'))
        return cursor.fetchall()
    finally:
        conn.close()

def atualizar_contato_db(contato_id, campos):
    """Atualiza um contato existente"""
    try:
        set_clause = ', '.join([f"{campo} = %s" for campo in campos.keys()])
        query = f'''
            UPDATE contatos 
            SET {set_clause}
            WHERE id = %s
        '''
        params = list(campos.values()) + [contato_id]
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar contato: {e}")
        return False
    finally:
        conn.close()

def apagar_contato_db(contato_id):
    """Desativa um contato (soft delete)"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE contatos 
            SET ativo = FALSE 
            WHERE id = %s
        ''', (contato_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao apagar contato: {e}")
        return False
    finally:
        conn.close()