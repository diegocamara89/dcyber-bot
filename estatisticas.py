import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database_estatisticas import get_db_connection, criar_tabela_estatisticas
from decorators import user_approved, admin_required
from datetime import datetime, timedelta


@user_approved
async def menu_estatisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Estatísticas Gerais", callback_data='stats_gerais')],
        [InlineKeyboardButton("👤 Minhas Estatísticas", callback_data='stats_pessoais')],
        [InlineKeyboardButton("🔙 Voltar", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="📊 Menu de Estatísticas\n\n"
             "Escolha uma opção:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def get_estatisticas_gerais():
    """Obtém estatísticas gerais do sistema"""
    try:
        criar_tabela_estatisticas()
    except Exception as e:
        print(f"Erro ao criar tabela de estatísticas: {e}")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        stats = {
            'usuarios': 0,
            'documentos': 0,
            'lembretes': 0,
            'contatos': 0,
            'casos': 0,
            'usuarios_ativos_hoje': 0,
            'documentos_pendentes': 0,
            'casos_ativos': 0
        }
        
        # Estatísticas básicas dos contadores
        try:
            cursor.execute('SELECT tipo, total FROM contadores_permanentes')
            for tipo, total in cursor.fetchall():
                stats[tipo] = total
        except Exception as e:
            print(f"Erro ao obter contadores: {e}")
        
        # Usuários ativos hoje
        hoje = datetime.now().strftime('%Y-%m-%d')
        try:
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) 
                FROM user_acessos 
                WHERE DATE(data_acesso) = ?
            ''', (hoje,))
            result = cursor.fetchone()
            stats['usuarios_ativos_hoje'] = result[0] if result else 0
        except Exception as e:
            print(f"Erro ao obter usuários ativos: {e}")
        
        # Documentos pendentes
        try:
            cursor.execute('SELECT COUNT(*) FROM assinaturas WHERE ativo = TRUE')
            result = cursor.fetchone()
            stats['documentos_pendentes'] = result[0] if result else 0
        except Exception as e:
            print(f"Erro ao obter documentos pendentes: {e}")
        
        # Casos ativos
        try:
            cursor.execute('SELECT COUNT(*) FROM casos WHERE ativo = TRUE')
            result = cursor.fetchone()
            stats['casos_ativos'] = result[0] if result else 0
        except Exception as e:
            print(f"Erro ao obter casos ativos: {e}")
        
        return stats
    except Exception as e:
        print(f"Erro geral em get_estatisticas_gerais: {e}")
        return {
            'usuarios': 0,
            'documentos': 0,
            'lembretes': 0,
            'contatos': 0,
            'casos': 0,
            'usuarios_ativos_hoje': 0,
            'documentos_pendentes': 0,
            'casos_ativos': 0
        }
    finally:
        conn.close()

def get_estatisticas_pessoais(user_id: int):
    """Obtém estatísticas pessoais do usuário"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        stats = {}
        
        # Ações do usuário
        for acao in ['novo_documento', 'novo_lembrete', 'novo_contato', 'novo_caso']:
            cursor.execute('''
                SELECT COUNT(*) 
                FROM acoes_usuarios 
                WHERE user_id = ? AND tipo_acao = ?
            ''', (user_id, acao))
            stats[acao] = cursor.fetchone()[0]
        
        # Últimos acessos
        cursor.execute('''
            SELECT data_acesso
            FROM user_acessos
            WHERE user_id = ?
            ORDER BY data_acesso DESC
            LIMIT 1
        ''', (user_id,))
        ultimo_acesso = cursor.fetchone()
        stats['ultimo_acesso'] = ultimo_acesso[0] if ultimo_acesso else None
        
        # Total de acessos
        cursor.execute('''
            SELECT COUNT(*)
            FROM user_acessos
            WHERE user_id = ?
        ''', (user_id,))
        stats['total_acessos'] = cursor.fetchone()[0]
        
        return stats
    finally:
        conn.close()

@user_approved
async def mostrar_estatisticas_gerais(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe estatísticas gerais do sistema"""
    stats = get_estatisticas_gerais()
    
    texto = "*📊 Estatísticas Gerais*\n\n"
    texto += "*👥 Usuários*\n"
    texto += f"• Total cadastrados: `{stats['usuarios']}`\n"
    texto += f"• Ativos hoje: `{stats['usuarios_ativos_hoje']}`\n\n"
    
    texto += "*📑 Documentos*\n"
    texto += f"• Total processados: `{stats['documentos']}`\n"
    texto += f"• Pendentes: `{stats['documentos_pendentes']}`\n\n"
    
    texto += "*📁 Casos*\n"
    texto += f"• Total registrados: `{stats['casos']}`\n"
    texto += f"• Em andamento: `{stats['casos_ativos']}`\n\n"
    
    texto += "*⏰ Lembretes*\n"
    texto += f"• Total criados: `{stats['lembretes']}`\n\n"
    
    texto += "*📇 Contatos*\n"
    texto += f"• Total cadastrados: `{stats['contatos']}`"

    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='estatisticas')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=texto,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

@user_approved
async def mostrar_estatisticas_pessoais(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe estatísticas pessoais do usuário"""
    user_id = update.callback_query.from_user.id
    stats = get_estatisticas_pessoais(user_id)
    
    texto = "*👤 Suas Estatísticas*\n\n"
    
    texto += "*📊 Atividades*\n"
    texto += f"• Documentos criados: `{stats['novo_documento']}`\n"
    texto += f"• Lembretes criados: `{stats['novo_lembrete']}`\n"
    texto += f"• Contatos cadastrados: `{stats['novo_contato']}`\n"
    texto += f"• Casos registrados: `{stats['novo_caso']}`\n\n"
    
    texto += "*🕐 Acessos*\n"
    texto += f"• Total de acessos: `{stats['total_acessos']}`\n"
    if stats['ultimo_acesso']:
        ultimo_acesso = datetime.strptime(stats['ultimo_acesso'], '%Y-%m-%d %H:%M:%S')
        texto += f"• Último acesso: `{ultimo_acesso.strftime('%d/%m/%Y %H:%M')}`"

    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='estatisticas')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=texto,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )