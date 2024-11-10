# auth.py
from database_manager import db

def is_admin(user_id: int) -> bool:
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT nivel FROM usuarios WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] == 'admin' if result else False
    finally:
        conn.close()

def is_user_approved(user_id: int) -> bool:
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT ativo FROM usuarios WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else False
    finally:
        conn.close()