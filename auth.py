from database import get_db_connection

def is_admin(user_id: int) -> bool:
    """Verifica se o usuário é admin"""
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
    """Verifica se o usuário é DPC"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT nivel FROM usuarios WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        return result[0] == 'dpc' if result else False
    finally:
        cursor.close()
        conn.close()

def is_user_active(user_id: int) -> bool:
    """Verifica se o usuário está ativo"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT ativo FROM usuarios WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else False
    finally:
        cursor.close()
        conn.close()

def get_user_level(user_id: int) -> str:
    """Obtém o nível do usuário"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT nivel FROM usuarios WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        conn.close()
