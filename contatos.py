# contatos.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from decorators import user_approved, admin_required
from datetime import datetime
from database_contatos import (
    adicionar_contato_db,
    consultar_contatos_db,
    pesquisar_contatos_db,
    apagar_contato_db
)
from database_estatisticas import incrementar_contador, registrar_acao_usuario

@user_approved
async def menu_contatos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Novo Contato", callback_data='contato_novo')],
        [InlineKeyboardButton("👥 Meus Contatos", callback_data='contato_listar')],
        [InlineKeyboardButton("🔍 Pesquisar", callback_data='contato_pesquisar')],
        [InlineKeyboardButton("🔙 Voltar", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="📇 Menu de Contatos\n\n"
             "Escolha uma opção:",
        reply_markup=reply_markup
    )

async def criar_contato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['criando_contato'] = True
    keyboard = [
        [InlineKeyboardButton("🔙 Cancelar", callback_data='contato_cancelar')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="👤 Novo Contato\n\n"
             "Digite as informações do contato no seguinte formato:\n\n"
             "Nome\n"
             "Contato (telefone/email)\n"
             "Observações (opcional)\n\n"
             "Exemplo:\n"
             "João Silva\n"
             "(11) 98765-4321\n"
             "Delegado da 1ª DP",
        reply_markup=reply_markup
    )

async def listar_contatos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    contatos = consultar_contatos_db(user_id)
    
    if not contatos:
        keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='contatos')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text="Você não possui contatos cadastrados.",
            reply_markup=reply_markup
        )
        return

    texto = "📇 Seus Contatos:\n\n"
    keyboard = []
    
    for contato in contatos:
        id_contato, nome, info_contato, obs, _ = contato
        texto += f"👤 {nome}\n"
        texto += f"📞 {info_contato}\n"
        if obs:
            texto += f"📝 {obs}\n"
        texto += "\n"
        keyboard.append([InlineKeyboardButton(
            f"❌ Apagar: {nome}",
            callback_data=f'contato_apagar_{id_contato}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='contatos')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=texto,
        reply_markup=reply_markup
    )

async def pesquisar_contatos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pesquisando_contato'] = True
    keyboard = [
        [InlineKeyboardButton("🔙 Cancelar", callback_data='contato_cancelar')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="🔍 Pesquisar Contatos\n\n"
             "Digite o nome ou parte do nome que deseja pesquisar:",
        reply_markup=reply_markup
    )

@user_approved
async def handle_contatos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'contatos':
        await menu_contatos(update, context)
    
    elif query.data == 'contato_novo':
        await criar_contato(update, context)
    
    elif query.data == 'contato_listar':
        await listar_contatos(update, context)
    
    elif query.data == 'contato_pesquisar':
        await pesquisar_contatos(update, context)
    
    elif query.data == 'contato_cancelar':
        context.user_data.clear()
        await menu_contatos(update, context)
    
    elif query.data.startswith('contato_apagar_'):
        contato_id = int(query.data.split('_')[-1])
        apagar_contato_db(contato_id)
        await listar_contatos(update, context)
    
    elif query.data == 'menu_principal':
        from dcyber_bot import start
        await start(update, context)

@user_approved
async def handle_contato_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('criando_contato'):
        try:
            linhas = update.message.text.split('\n')
            if len(linhas) < 2:
                await update.message.reply_text(
                    "❌ Formato inválido!\n\n"
                    "Use o formato:\n"
                    "Nome\n"
                    "Contato\n"
                    "Observações (opcional)"
                )
                return

            nome = linhas[0].strip()
            contato = linhas[1].strip()
            observacoes = linhas[2].strip() if len(linhas) > 2 else None

            user_id = update.effective_user.id
            contato_id = adicionar_contato_db(user_id, nome, contato, observacoes)
            
            if contato_id:
                texto_resposta = "✅ Contato adicionado com sucesso!\n\n"
                texto_resposta += f"👤 Nome: {nome}\n"
                texto_resposta += f"📞 Contato: {contato}\n"
                if observacoes:
                    texto_resposta += f"📝 Obs: {observacoes}\n"
                
                keyboard = [
                    [InlineKeyboardButton("📇 Menu Contatos", callback_data='contatos')],
                    [InlineKeyboardButton("🏠 Menu Principal", callback_data='menu_principal')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    texto_resposta,
                    reply_markup=reply_markup
                )
                
                # Registrar estatísticas
                incrementar_contador('contatos')
                registrar_acao_usuario(user_id, 'novo_contato')
            else:
                await update.message.reply_text("❌ Erro ao adicionar contato.")
            
        except Exception as e:
            print(f"Erro ao criar contato: {e}")
            await update.message.reply_text("❌ Erro ao criar contato. Tente novamente.")
        finally:
            context.user_data.pop('criando_contato', None)
    
    elif context.user_data.get('pesquisando_contato'):
        try:
            termo = update.message.text.strip()
            user_id = update.effective_user.id
            contatos = pesquisar_contatos_db(user_id, termo)
            
            if not contatos:
                keyboard = [
                    [InlineKeyboardButton("🔍 Nova Pesquisa", callback_data='contato_pesquisar')],
                    [InlineKeyboardButton("📇 Menu Contatos", callback_data='contatos')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "❌ Nenhum contato encontrado.",
                    reply_markup=reply_markup
                )
                return
            
            texto = "🔍 Resultados da pesquisa:\n\n"
            for id_contato, nome, info_contato, obs, _ in contatos:
                texto += f"👤 {nome}\n"
                texto += f"📞 {info_contato}\n"
                if obs:
                    texto += f"📝 {obs}\n"
                texto += "\n"
            
            keyboard = [
                [InlineKeyboardButton("🔍 Nova Pesquisa", callback_data='contato_pesquisar')],
                [InlineKeyboardButton("📇 Menu Contatos", callback_data='contatos')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                texto,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            print(f"Erro ao pesquisar contatos: {e}")
            await update.message.reply_text("❌ Erro ao pesquisar contatos. Tente novamente.")
        finally:
            context.user_data.pop('pesquisando_contato', None)