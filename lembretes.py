# lembretes.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from database import (
    get_db_connection,
    get_usuarios_cadastrados,
    get_user_display_info
)
from database_estatisticas import incrementar_contador, registrar_acao_usuario
from decorators import user_approved, admin_required
from telegram.constants import ParseMode

# Estados para o lembrete
TITULO = 'titulo'
DATA = 'data'
HORA = 'hora'
DESTINATARIOS = 'destinatarios'

@user_approved
async def menu_lembretes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal de lembretes"""
    keyboard = [
        [InlineKeyboardButton("➕ Novo Lembrete", callback_data='lembrete_novo')],
        [InlineKeyboardButton("📋 Meus Lembretes", callback_data='lembrete_listar')],
        [InlineKeyboardButton("🔙 Voltar", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="⏰ *Menu de Lembretes*\n\n"
             "Escolha uma opção:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def criar_lembrete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o processo de criação de um novo lembrete"""
    context.user_data['criando_lembrete'] = True
    context.user_data['estado_lembrete'] = TITULO
    context.user_data['destinatarios'] = []
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data='lembrete_cancelar')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="📝 *Novo Lembrete*\n\n"
             "Qual o título do lembrete?",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def selecionar_destinatarios_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu de seleção de destinatários"""
    keyboard = [
        [InlineKeyboardButton("👤 Apenas eu", callback_data='lembrete_dest_eu')],
        [InlineKeyboardButton("👥 Selecionar usuários", callback_data='lembrete_dest_selecionar')],
        [InlineKeyboardButton("📢 Todos os usuários", callback_data='lembrete_dest_todos')],
        [InlineKeyboardButton("🔙 Cancelar", callback_data='lembrete_cancelar')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        text="🔔 *Destinatários do Lembrete*\n\n"
             "Quem deve receber este lembrete?",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def selecionar_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interface de seleção de usuários específicos"""
    current_user_id = update.callback_query.from_user.id
    current_user = get_user_display_info(user_id=current_user_id)
    outros_usuarios = get_usuarios_cadastrados(excluir_user_id=current_user_id)
    
    if not outros_usuarios and not current_user:
        await update.callback_query.edit_message_text(
            text="❌ Não há usuários cadastrados no sistema.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Voltar", callback_data='lembrete_dest_voltar')
            ]])
        )
        return

    keyboard = []
    texto = "👥 *Selecione os destinatários:*\n(Clique para marcar/desmarcar)"
    destinatarios = context.user_data.get('destinatarios', [])
    
    # Adiciona o usuário atual (se for ativo e não pendente)
    if current_user and current_user.get('nivel') != 'pendente':
        selecionado = str(current_user_id) in destinatarios
        emoji = "✅" if selecionado else "⭕"
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {current_user['display_name']} (Você)",
                callback_data=f'lembrete_user_{current_user_id}'
            )
        ])
    
    # Adiciona outros usuários
    for user_id, display_name in outros_usuarios:
        selecionado = str(user_id) in destinatarios
        emoji = "✅" if selecionado else "⭕"
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {display_name}",
                callback_data=f'lembrete_user_{user_id}'
            )
        ])
    
    if destinatarios:
        texto += "\n\n📌 *Selecionados:*"
        for dest_id in destinatarios:
            user_info = get_user_display_info(user_id=int(dest_id))
            if user_info:
                texto += f"\n• {user_info['display_name']}"
    
    keyboard.append([InlineKeyboardButton("✅ Confirmar", callback_data='lembrete_dest_confirmar')])
    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='lembrete_dest_voltar')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(
        texto,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def finalizar_lembrete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finaliza a criação do lembrete"""
    try:
        user_id = update.callback_query.from_user.id
        titulo = context.user_data['titulo']
        data = context.user_data['data']
        hora = context.user_data['hora']
        destinatarios = context.user_data.get('destinatarios', [])
        
        lembrete_id = adicionar_lembrete_db(
            user_id, 
            titulo, 
            data.strftime('%Y-%m-%d'),
            hora.strftime('%H:%M'),
            destinatarios
        )
        
        if lembrete_id:
            await update.callback_query.message.edit_text(
                "✅ *Lembrete criado com sucesso!*\n\n"
                f"📝 Título: {titulo}\n"
                f"📅 Data: {data.strftime('%d/%m/%Y')}\n"
                f"⏰ Hora: {hora.strftime('%H:%M')}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='lembretes')
                ]])
            )
        
        context.user_data.clear()
        return lembrete_id
        
    except Exception as e:
        print(f"Erro ao finalizar lembrete: {e}")
        await update.callback_query.message.edit_text(
            "❌ Erro ao criar lembrete. Tente novamente.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Voltar", callback_data='lembretes')
            ]])
        )
        return None

async def listar_lembretes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista os lembretes do usuário"""
    user_id = update.callback_query.from_user.id
    lembretes = consultar_lembretes_db(user_id)
    
    if not lembretes:
        keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='lembretes')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text="📝 *Meus Lembretes*\n\n"
                 "Você não possui lembretes cadastrados.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return

    texto = "📋 *Meus Lembretes:*\n\n"
    keyboard = []
    
    for lembrete in lembretes:
        id_lembrete, titulo, data, hora, destinatarios = lembrete
        texto += f"📌 *{titulo}*\n"
        texto += f"📅 {data} às {hora}\n"
        texto += f"👥 Para: {destinatarios}\n\n"
        keyboard.append([InlineKeyboardButton(
            f"❌ Apagar: {titulo}",
            callback_data=f'lembrete_apagar_{id_lembrete}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='lembretes')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=texto,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def adicionar_lembrete_db(user_id: int, titulo: str, data: str, hora: str, destinatarios: list):
    """Adiciona um novo lembrete no banco de dados"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO lembretes (criador_id, titulo, data, hora, ativo)
        VALUES (?, ?, ?, ?, TRUE)
        ''', (user_id, titulo, data, hora))
        lembrete_id = cursor.lastrowid
        
        if not destinatarios:  # Se vazio, apenas o criador
            destinatarios = [user_id]
        elif 'todos' in destinatarios:
            cursor.execute('SELECT user_id FROM usuarios WHERE ativo = TRUE AND nivel != "pendente"')
            destinatarios = [row[0] for row in cursor.fetchall()]
        
        for dest_id in destinatarios:
            cursor.execute('''
            INSERT INTO lembrete_destinatarios (lembrete_id, user_id, notificado)
            VALUES (?, ?, FALSE)
            ''', (lembrete_id, dest_id))
        
        conn.commit()
        incrementar_contador('lembretes')
        registrar_acao_usuario(user_id, 'novo_lembrete')
        return lembrete_id
    finally:
        conn.close()

def consultar_lembretes_db(user_id: int):
    """Consulta os lembretes do usuário"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        SELECT l.id, l.titulo, l.data, l.hora,
               GROUP_CONCAT(
                   CASE 
                       WHEN u.nome LIKE '% %' THEN substr(u.nome, 1, instr(u.nome, ' ')-1)
                       ELSE u.nome
                   END, 
                   ', '
               ) as destinatarios
        FROM lembretes l
        JOIN lembrete_destinatarios ld ON l.id = ld.lembrete_id
        LEFT JOIN usuarios u ON ld.user_id = u.user_id
        WHERE l.ativo = TRUE 
        AND (l.criador_id = ? OR ld.user_id = ?)
        GROUP BY l.id
        ORDER BY l.data ASC, l.hora ASC
        ''', (user_id, user_id))
        return cursor.fetchall()
    finally:
        conn.close()

def apagar_lembrete_db(lembrete_id: int):
    """Apaga (desativa) um lembrete"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE lembretes SET ativo = FALSE WHERE id = ?', (lembrete_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao apagar lembrete: {e}")
        return False
    finally:
        conn.close()

@user_approved
async def handle_lembretes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler principal para callbacks de lembretes"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'lembretes':
        await menu_lembretes(update, context)
    
    elif query.data == 'lembrete_novo':
        await criar_lembrete(update, context)
    
    elif query.data == 'lembrete_listar':
        await listar_lembretes(update, context)
    
    elif query.data == 'lembrete_cancelar':
        context.user_data.clear()
        await menu_lembretes(update, context)
    
    elif query.data == 'lembrete_dest_eu':
        context.user_data['destinatarios'] = []  # Apenas o criador
        lembrete_id = await finalizar_lembrete(update, context)
        if lembrete_id:
            await menu_lembretes(update, context)
    
    elif query.data == 'lembrete_dest_todos':
        context.user_data['destinatarios'] = ['todos']
        lembrete_id = await finalizar_lembrete(update, context)
        if lembrete_id:
            await menu_lembretes(update, context)
    
    elif query.data == 'lembrete_dest_selecionar':
        await selecionar_usuarios(update, context)
    
    elif query.data == 'lembrete_dest_voltar':
        await selecionar_destinatarios_callback(update, context)
    
    elif query.data.startswith('lembrete_user_'):
        user_id = query.data.split('_')[-1]
        destinatarios = context.user_data.get('destinatarios', [])
        
        if user_id in destinatarios:
            destinatarios.remove(user_id)
        else:
            destinatarios.append(user_id)
        
        context.user_data['destinatarios'] = destinatarios
        await selecionar_usuarios(update, context)
    
    elif query.data == 'lembrete_dest_confirmar':
        if context.user_data.get('destinatarios'):
            lembrete_id = await finalizar_lembrete(update, context)
            if lembrete_id:
                await menu_lembretes(update, context)
        else:
            await query.edit_message_text(
                "⚠️ Selecione pelo menos um destinatário!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='lembrete_dest_selecionar')
                ]])
            )
    
    elif query.data.startswith('lembrete_apagar_'):
        lembrete_id = int(query.data.split('_')[-1])
        if apagar_lembrete_db(lembrete_id):
            await listar_lembretes(update, context)
        else:
            await query.edit_message_text(
                "❌ Erro ao apagar lembrete",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='lembrete_listar')
                ]])
            )

@user_approved
async def handle_lembrete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para mensagens durante criação de lembretes"""
    if not context.user_data.get('criando_lembrete'):
        return

    estado = context.user_data.get('estado_lembrete')
    texto = update.message.text.strip()

    if estado == TITULO:
        context.user_data['titulo'] = texto
        context.user_data['estado_lembrete'] = DATA
        await update.message.reply_text(
            "📅 *Data do Lembrete*\n\n"
            "Digite a data no formato DD/MM/YYYY\n"
            "Exemplo: 25/12/2024",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif estado == DATA:
        try:
            data = datetime.strptime(texto, "%d/%m/%Y")
            context.user_data['data'] = data
            context.user_data['estado_lembrete'] = HORA
            await update.message.reply_text(
                "⏰ *Hora do Lembrete*\n\n"
                "Digite a hora no formato HH:MM\n"
                "Exemplo: 14:30",
                parse_mode=ParseMode.MARKDOWN
            )
        except ValueError:
            await update.message.reply_text("❌ Data inválida! Use o formato DD/MM/YYYY")
    
    elif estado == HORA:
        try:
            hora = datetime.strptime(texto, "%H:%M").time()
            data = context.user_data['data']
            data_hora = datetime.combine(data.date(), hora)
            
            if data_hora < datetime.now():
                await update.message.reply_text(
                    "❌ Não é possível criar lembretes para datas passadas!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Voltar", callback_data='lembretes')
                    ]])
                )
                context.user_data.clear()
                return
            
            context.user_data['hora'] = hora
            context.user_data['estado_lembrete'] = DESTINATARIOS
            
            keyboard = [
                [InlineKeyboardButton("👤 Apenas eu", callback_data='lembrete_dest_eu')],
                [InlineKeyboardButton("👥 Selecionar usuários", callback_data='lembrete_dest_selecionar')],
                [InlineKeyboardButton("📢 Todos os usuários", callback_data='lembrete_dest_todos')],
                [InlineKeyboardButton("🔙 Cancelar", callback_data='lembrete_cancelar')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔔 *Destinatários do Lembrete*\n\n"
                "Quem deve receber este lembrete?",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except ValueError:
            await update.message.reply_text("❌ Hora inválida! Use o formato HH:MM")
        except Exception as e:
            await update.message.reply_text("❌ Erro ao criar lembrete. Tente novamente.")
            context.user_data.clear()

async def verificar_lembretes(context: ContextTypes.DEFAULT_TYPE):
    """Verifica lembretes pendentes e envia notificações"""
    agora = datetime.now()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT l.id, ld.user_id, l.titulo, l.data, l.hora
            FROM lembretes l
            JOIN lembrete_destinatarios ld ON l.id = ld.lembrete_id
            WHERE l.data = ? 
            AND l.hora <= ?
            AND ld.notificado = FALSE
            AND l.ativo = TRUE
        ''', (agora.strftime('%Y-%m-%d'), agora.strftime('%H:%M')))
        
        lembretes = cursor.fetchall()
        
        for lembrete_id, user_id, titulo, data, hora in lembretes:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🔔 *Lembrete!*\n\n"
                         f"📝 {titulo}\n"
                         f"⏰ Agendado para hoje às {hora}",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                cursor.execute('''
                    UPDATE lembrete_destinatarios 
                    SET notificado = TRUE 
                    WHERE lembrete_id = ? AND user_id = ?
                ''', (lembrete_id, user_id))
                conn.commit()
                
            except Exception as e:
                print(f"Erro ao enviar notificação: {e}")
                
    except Exception as e:
        print(f"Erro ao verificar lembretes: {e}")
    finally:
        conn.close()