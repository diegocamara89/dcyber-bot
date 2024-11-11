from database_manager import db
from database_estatisticas import incrementar_contador

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
        cursor.close()
        conn.close()

def adicionar_contato_db(user_id, nome, contato, observacoes=None):
    """Adiciona um novo contato"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO contatos (user_id, nome, contato, observacoes)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        ''', (user_id, nome, contato, observacoes))
        result = cursor.fetchone()
        conn.commit()
        if result:
            incrementar_contador('contatos')
        return result[0] if result else None
    except Exception as e:
        print(f"Erro ao adicionar contato: {e}")
        return None
    finally:
        cursor.close()
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
            query += ' AND (nome ILIKE %s OR contato ILIKE %s OR observacoes ILIKE %s)'
            busca_param = f'%{busca}%'
            params.extend([busca_param, busca_param, busca_param])
        
        query += ' ORDER BY nome'
        
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
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
        AND (
            nome ILIKE %s 
            OR contato ILIKE %s 
            OR observacoes ILIKE %s
        )
        ORDER BY nome ASC
        ''', (user_id, f'%{termo}%', f'%{termo}%', f'%{termo}%'))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def atualizar_contato_db(contato_id, campos):
    """Atualiza um contato existente"""
    try:
        set_clause = ', '.join([f"{campo} = %s" for campo in campos.keys()])
        query = f'''
            UPDATE contatos 
            SET {set_clause}
            WHERE id = %s
            RETURNING id
        '''
        params = list(campos.values()) + [contato_id]
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.commit()
        return bool(result)
    except Exception as e:
        print(f"Erro ao atualizar contato: {e}")
        return False
    finally:
        cursor.close()
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
            RETURNING id
        ''', (contato_id,))
        result = cursor.fetchone()
        conn.commit()
        return bool(result)
    except Exception as e:
        print(f"Erro ao apagar contato: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
