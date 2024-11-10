# database_casos.py
from database_manager import db
from datetime import datetime

def criar_tabela_casos():
    """Cria tabelas relacionadas a casos"""
    queries = [
        '''
        CREATE TABLE IF NOT EXISTS casos (
            id SERIAL PRIMARY KEY,
            titulo TEXT NOT NULL,
            observacoes TEXT,
            status TEXT NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo BOOLEAN DEFAULT TRUE
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS caso_responsaveis (
            id SERIAL PRIMARY KEY,
            caso_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            FOREIGN KEY (caso_id) REFERENCES casos (id),
            FOREIGN KEY (user_id) REFERENCES usuarios (user_id)
        )
        '''
    ]
    
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        for query in queries:
            cursor.execute(query)
        conn.commit()
    finally:
        conn.close()

def adicionar_caso_db(titulo, responsaveis, observacoes, status):
    """Adiciona um novo caso"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO casos (titulo, observacoes, status)
            VALUES (%s, %s, %s)
        ''', (titulo, observacoes, status))
        
        caso_id = cursor.lastrowid
        
        for user_id in responsaveis:
            cursor.execute('''
                INSERT INTO caso_responsaveis (caso_id, user_id)
                VALUES (%s, %s)
            ''', (caso_id, int(user_id)))
        
        conn.commit()
        return caso_id
    except Exception as e:
        print(f"Erro ao adicionar caso: {str(e)}")
        conn.rollback()
        raise e
    finally:
        conn.close()

def atualizar_caso_db(caso_id, campo, valor):
    """Atualiza um caso existente"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        if campo == 'responsaveis':
            cursor.execute('DELETE FROM caso_responsaveis WHERE caso_id = %s', (caso_id,))
            for user_id in valor:
                cursor.execute('''
                    INSERT INTO caso_responsaveis (caso_id, user_id)
                    VALUES (%s, %s)
                ''', (caso_id, int(user_id)))
        else:
            cursor.execute(f'''
                UPDATE casos 
                SET {campo} = %s, 
                    ultima_atualizacao = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (valor, caso_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar caso: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def apagar_caso_db(caso_id):
    """Apaga um caso permanentemente"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        # Primeiro apaga os responsáveis
        cursor.execute('DELETE FROM caso_responsaveis WHERE caso_id = %s', (caso_id,))
        # Depois apaga o caso
        cursor.execute('DELETE FROM casos WHERE id = %s', (caso_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao apagar caso: {e}")
        return False
    finally:
        conn.close()

def consultar_casos_db():
    """Consulta casos com informações formatadas"""
    from database import get_user_display_info
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT 
                c.id, 
                c.titulo, 
                c.observacoes, 
                c.status,
                GROUP_CONCAT(cr.user_id) as responsaveis_ids,
                c.data_criacao
            FROM casos c
            LEFT JOIN caso_responsaveis cr ON c.id = cr.caso_id
            WHERE c.ativo = TRUE
            GROUP BY c.id
            ORDER BY c.data_criacao DESC
        ''')
        
        casos_raw = cursor.fetchall()
        casos_formatados = []
        
        for caso in casos_raw:
            id_caso, titulo, observacoes, status, responsaveis_ids, data = caso
            responsaveis_nomes = []
            
            if responsaveis_ids:
                for user_id in responsaveis_ids.split(','):
                    user_info = get_user_display_info(user_id=int(user_id))
                    if user_info:
                        responsaveis_nomes.append(user_info['display_name'])
            
            responsaveis_texto = ', '.join(responsaveis_nomes) if responsaveis_nomes else 'Nenhum'
            
            casos_formatados.append((
                id_caso,
                titulo,
                observacoes,
                status,
                responsaveis_texto,
                data
            ))
        
        return casos_formatados
    except Exception as e:
        print(f"Erro ao consultar casos: {e}")
        return []
    finally:
        conn.close()

def encerrar_caso_db(caso_id):
    """Encerra um caso"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE casos 
            SET ativo = FALSE,
                status = '✅ Encerrado',
                ultima_atualizacao = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (caso_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao encerrar caso: {e}")
        return False
    finally:
        conn.close()