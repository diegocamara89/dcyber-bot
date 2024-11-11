from database_manager import db
from database_estatisticas import incrementar_contador

def criar_tabela_casos():
    """Cria a tabela de casos"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS casos (
                id SERIAL PRIMARY KEY,
                criador_id BIGINT NOT NULL,
                titulo TEXT NOT NULL,
                descricao TEXT,
                observacoes TEXT,
                status TEXT DEFAULT 'Aberto',
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (criador_id) REFERENCES usuarios (user_id)
            )
        ''')
        
        # Tabela para responsáveis dos casos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caso_responsaveis (
                id SERIAL PRIMARY KEY,
                caso_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                FOREIGN KEY (caso_id) REFERENCES casos (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES usuarios (user_id),
                UNIQUE(caso_id, user_id)
            )
        ''')
        
        conn.commit()
    except Exception as e:
        print(f"Erro ao criar tabela de casos: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

def adicionar_caso_db(user_id: int, titulo: str, descricao: str, observacoes: str = None):
    """Adiciona um novo caso"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO casos (criador_id, titulo, descricao, observacoes)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        ''', (user_id, titulo, descricao, observacoes))
        
        caso_id = cursor.fetchone()[0]
        
        # Adiciona o criador como responsável
        cursor.execute('''
            INSERT INTO caso_responsaveis (caso_id, user_id)
            VALUES (%s, %s)
        ''', (caso_id, user_id))
        
        conn.commit()
        incrementar_contador('casos')
        return caso_id
    except Exception as e:
        print(f"Erro ao adicionar caso: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def consultar_casos_db():
    """Consulta casos ativos"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT 
                c.id,
                c.titulo,
                c.observacoes,
                c.status,
                string_agg(
                    CASE 
                        WHEN u.nome LIKE %s THEN split_part(u.nome, ' ', 1)
                        ELSE u.nome
                    END,
                    ', '
                ) as responsaveis,
                c.criado_em
            FROM casos c
            LEFT JOIN caso_responsaveis cr ON c.id = cr.caso_id
            LEFT JOIN usuarios u ON cr.user_id = u.user_id
            WHERE c.ativo = TRUE
            GROUP BY c.id
            ORDER BY c.criado_em DESC
        ''', ('% %',))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def atualizar_caso_db(caso_id: int, campo: str, valor: str):
    """Atualiza um campo específico do caso"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        if campo == 'responsaveis':
            # Primeiro remove todos os responsáveis atuais
            cursor.execute('''
                DELETE FROM caso_responsaveis 
                WHERE caso_id = %s
            ''', (caso_id,))
            
            # Adiciona os novos responsáveis
            for user_id in valor:
                cursor.execute('''
                    INSERT INTO caso_responsaveis (caso_id, user_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                ''', (caso_id, int(user_id)))
        else:
            cursor.execute(f'''
                UPDATE casos 
                SET {campo} = %s
                WHERE id = %s
                RETURNING id
            ''', (valor, caso_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar caso: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def encerrar_caso_db(caso_id: int):
    """Encerra um caso"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE casos 
            SET ativo = FALSE, 
                status = 'Encerrado'
            WHERE id = %s
            RETURNING id
        ''', (caso_id,))
        result = cursor.fetchone()
        conn.commit()
        return bool(result)
    except Exception as e:
        print(f"Erro ao encerrar caso: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def apagar_caso_db(caso_id: int):
    """Apaga um caso (soft delete)"""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE casos 
            SET ativo = FALSE 
            WHERE id = %s
            RETURNING id
        ''', (caso_id,))
        result = cursor.fetchone()
        conn.commit()
        return bool(result)
    except Exception as e:
        print(f"Erro ao apagar caso: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
