# dcyber-bot.py
import os
import pytz
from datetime import datetime, timedelta

TIMEZONE = pytz.timezone('America/Sao_Paulo')
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    JobQueue
)

# Database imports
from database_manager import db
from database import (
    criar_tabela, 
    criar_tabela_lembretes, 
    criar_tabela_usuarios,
    criar_tabela_acessos,
    criar_todas_tabelas,
    get_db_connection,
    listar_usuarios,
    obter_id_dpc,
    registrar_acesso,
    registrar_novo_usuario,
    atualizar_nome_admin,
    is_admin  # Adicione esta importação
)
from database_estatisticas import (  # Adicione esta importação
    criar_tabela_estatisticas,
    incrementar_contador,
    registrar_acao_usuario
)

# Feature handlers
from casos import menu_casos, handle_casos_callback, handle_caso_message
from contatos import menu_contatos, handle_contatos_callback, handle_contato_message
from database_contatos import criar_tabela_contatos
from database_casos import criar_tabela_casos
from lembretes import (
    menu_lembretes, 
    handle_lembretes_callback, 
    handle_lembrete_message,
    verificar_lembretes
)
from assinaturas import button_handler, adicionar_assinatura, create_admin_notification_markup
from estatisticas import menu_estatisticas, mostrar_estatisticas_gerais, mostrar_estatisticas_pessoais
from ajuda import menu_ajuda, comando_ajuda, handle_ajuda_callback
from admin import (
    menu_admin, 
    handle_admin_callback, 
    processar_id_dpc,
    menu_usuarios,
    menu_relatorios,
    solicitar_id_dpc,
    solicitar_mensagem,
    processar_mensagem  # Adicione estas
)
from decorators import admin_required, user_approved

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = 1697670772

def verificar_usuario_ativo(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT ativo, nivel FROM usuarios WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        is_active = result[0] if result else False
        nivel = result[1] if result else None
        print(f"Verificação de usuário - ID: {user_id}, Ativo: {is_active}, Nível: {nivel}")
        return is_active
    finally:
        cursor.close()
        conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    username = update.effective_user.username
    
    print(f"Start command - User ID: {user_id}, Name: {user_name}, Username: {username}")
    
    if user_id != ADMIN_ID:
        registrar_novo_usuario(
            user_id=user_id,
            nome=user_name,
            username=username
        )
    
    registrar_acesso(user_id, 'login')
    
    if user_id != ADMIN_ID:
        is_active = verificar_usuario_ativo(user_id)
        print(f"Status do usuário {user_id}: {'Ativo' if is_active else 'Inativo'}")
        
        if not is_active:
            await update.message.reply_text(
                "👋 Bem-vindo ao Dcyber Bot!\n\n"
                "⚠️ Seu acesso está pendente de aprovação.\n"
                "Por favor, aguarde a aprovação do administrador."
            )
            return

    keyboard = [
        [InlineKeyboardButton("📑 Assinaturas", callback_data='assinaturas')],
        [InlineKeyboardButton("📇 Contatos", callback_data='contatos')],
        [InlineKeyboardButton("⏰ Lembretes", callback_data='lembretes')],
        [InlineKeyboardButton("📁 Casos", callback_data='casos')],
        [InlineKeyboardButton("📊 Estatísticas", callback_data='estatisticas')],
        [InlineKeyboardButton("❓ Ajuda", callback_data='ajuda')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update, 'message') and update.message:
        await update.message.reply_text('👋 Bem-vindo ao Dcyber Bot! Escolha uma opção:', reply_markup=reply_markup)
    elif hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text('👋 Bem-vindo ao Dcyber Bot! Escolha uma opção:', reply_markup=reply_markup)
        await update.callback_query.answer()

@user_approved
async def assinaturas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("✍️ Solicitar Assinatura", callback_data='solicitar_assinatura')],
        [InlineKeyboardButton("🔍 Consultar Assinatura", callback_data='consultar_assinatura')],
        [InlineKeyboardButton("🔙 Menu Principal", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📑 Menu de Assinaturas", reply_markup=reply_markup)

@user_approved
async def casos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atalho para o menu de casos"""
    keyboard = [
        [InlineKeyboardButton("📁 Novo Caso", callback_data='caso_novo')],
        [InlineKeyboardButton("📋 Meus Casos", callback_data='caso_listar')],
        [InlineKeyboardButton("🔍 Pesquisar", callback_data='caso_pesquisar')],
        [InlineKeyboardButton("🔙 Menu Principal", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📁 Menu de Casos", reply_markup=reply_markup)

@user_approved
async def contatos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atalho para o menu de contatos"""
    keyboard = [
        [InlineKeyboardButton("➕ Novo Contato", callback_data='contato_novo')],
        [InlineKeyboardButton("👥 Meus Contatos", callback_data='contato_listar')],
        [InlineKeyboardButton("🔍 Pesquisar", callback_data='contato_pesquisar')],
        [InlineKeyboardButton("🔙 Menu Principal", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📇 Menu de Contatos", reply_markup=reply_markup)

@user_approved
async def lembretes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atalho para o menu de lembretes"""
    keyboard = [
        [InlineKeyboardButton("➕ Novo Lembrete", callback_data='lembrete_novo')],
        [InlineKeyboardButton("📋 Meus Lembretes", callback_data='lembrete_listar')],
        [InlineKeyboardButton("🔙 Menu Principal", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⏰ Menu de Lembretes", reply_markup=reply_markup)

@user_approved
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atalho para o menu de estatísticas"""
    keyboard = [
        [InlineKeyboardButton("📊 Estatísticas Gerais", callback_data='stats_gerais')],
        [InlineKeyboardButton("👤 Minhas Estatísticas", callback_data='stats_pessoais')],
        [InlineKeyboardButton("🔙 Menu Principal", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📊 Menu de Estatísticas", reply_markup=reply_markup)

@user_approved
async def texto_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('esperando_documento'):
        texto = update.message.text.strip()
        if not texto:
            await update.message.reply_text("⚠️ Por favor, digite o texto do documento.")
            return
            
        documentos = texto.split('\n')
        user_id = update.message.from_user.id
        username = update.message.from_user.first_name or update.message.from_user.username

        num_documentos_adicionados = 0
        documentos_adicionados = []

        for documento in documentos:
            documento = documento.strip()
            if documento:
                try:
                    seq = adicionar_assinatura(user_id, username, documento)
                    if seq:
                        documentos_adicionados.append((documento, seq))
                        num_documentos_adicionados += 1
                except Exception as e:
                    print(f"Erro ao processar documento: {e}")
                    await update.message.reply_text(f"❌ Erro ao processar documento: {str(e)}")
                    continue

        if num_documentos_adicionados > 0:
            await update.message.reply_text(
                f"✅ {num_documentos_adicionados} documento(s) cadastrado(s) para assinatura. O DPC será notificado."
            )

            dpc_id = obter_id_dpc()
            print(f"DPC ID obtido: {dpc_id}")
            
            if dpc_id:
                for documento, seq in documentos_adicionados:
                    try:
                        mensagem_dpc = (
                            f"📄 Nova solicitação #{seq}\n"
                            f"👤 Solicitante: {username}\n"
                            f"📝 Documento: {documento}"
                        )
                        reply_markup = await create_admin_notification_markup(seq)
                        
                        print(f"Tentando enviar notificação para DPC ID {dpc_id}")
                        await context.bot.send_message(
                            chat_id=dpc_id,
                            text=mensagem_dpc,
                            reply_markup=reply_markup
                        )
                        print("Notificação enviada com sucesso")
                        
                    except Exception as e:
                        print(f"Erro detalhado ao enviar notificação para DPC: {str(e)}")
                        try:
                            await context.bot.send_message(
                                chat_id=ADMIN_ID,
                                text=f"⚠️ Erro ao notificar DPC. Por favor, verifique:\n{mensagem_dpc}\nErro: {str(e)}",
                                reply_markup=reply_markup
                            )
                        except Exception as admin_error:
                            print(f"Erro ao enviar fallback para admin: {str(admin_error)}")
            else:
                print("Nenhum DPC definido no sistema")
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text="⚠️ Não há DPC definido no sistema. Por favor, defina um DPC.",
                )
        else:
            await update.message.reply_text("⚠️ Nenhum documento válido foi encontrado. Tente novamente.")
        
        context.user_data['esperando_documento'] = False

@user_approved
async def button_handler_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    print(f"button_handler_main recebeu callback: {query.data}")
    await query.answer()
    
    admin_callbacks = [
        'admin_usuarios', 'admin_relatorios', 'admin_config',
        'definir_dpc', 'menu_admin', 'menu_relatorios',
        'relatorio_hoje', 'relatorio_semana', 'relatorio_mes', 'relatorio_mes_anterior',
        'config_gerais', 'config_seguranca', 'admin_gerenciar_usuarios',
        'admin_enviar_mensagem', 'cancelar_envio'
    ]
    
    # Adicionar verificação para callbacks de mensagens
    if query.data.startswith('msg_') or query.data.startswith('enviar_msg_'):
        if is_admin(query.from_user.id):
            await solicitar_mensagem(update, context)
        return
    
    if query.data in admin_callbacks or query.data.startswith('admin_'):
        print(f"Encaminhando para handle_admin_callback: {query.data}")
        await handle_admin_callback(update, context)
    elif query.data == 'ajuda' or query.data.startswith('ajuda_'):
        await handle_ajuda_callback(update, context)
    elif query.data == 'lembretes':
        await menu_lembretes(update, context)
    elif query.data.startswith('lembrete_'):
        await handle_lembretes_callback(update, context)
    elif query.data == 'casos' or query.data.startswith('caso_'):
        await handle_casos_callback(update, context)
    elif query.data == 'contatos':
        await menu_contatos(update, context)
    elif query.data.startswith('contato_'):
        await handle_contatos_callback(update, context)
    elif query.data == 'estatisticas':
        await menu_estatisticas(update, context)
    elif query.data == 'stats_gerais':
        await mostrar_estatisticas_gerais(update, context)
    elif query.data == 'stats_pessoais':
        await mostrar_estatisticas_pessoais(update, context)
    elif query.data == 'menu_principal':
        await start(update, context)
    elif query.data == 'assinaturas':
        keyboard = [
            [InlineKeyboardButton("✍️ Solicitar Assinatura", callback_data='solicitar_assinatura')],
            [InlineKeyboardButton("🔍 Consultar Assinatura", callback_data='consultar_assinatura')],
            [InlineKeyboardButton("🔙 Menu Principal", callback_data='menu_principal')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("📑 Menu de Assinaturas", reply_markup=reply_markup)
    elif query.data in ['solicitar_assinatura', 'consultar_assinatura']:
        await button_handler(update, context)
    else:
        await button_handler(update, context)

@user_approved
async def handle_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Recebida mensagem: {update.message.text}")
    print(f"Estado do contexto: {context.user_data}")
    
    if context.user_data.get('criando_caso'):
        await handle_caso_message(update, context)
    elif context.user_data.get('editando') and context.user_data.get('caso_selecionado'):
        from casos import handle_caso_edicao_message
        await handle_caso_edicao_message(update, context)
    elif context.user_data.get('esperando_documento'):
        print("Processando documento")
        await texto_handler(update, context)
    elif context.user_data.get('esperando_id_dpc'):
        print("Processando ID do DPC")
        await processar_id_dpc(update, context)
    elif context.user_data.get('criando_lembrete'):
        print("Processando lembrete")
        await handle_lembrete_message(update, context)
    elif context.user_data.get('criando_contato') or context.user_data.get('pesquisando_contato'):
        print("Processando contato")
        await handle_contato_message(update, context)
    elif context.user_data.get('envio_mensagem', {}).get('aguardando_texto'):
        await processar_mensagem(update, context)

async def cancelar_operacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela a operação atual e limpa o contexto"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Operação cancelada.\n"
        "Use /start para voltar ao menu principal."
    )

@user_approved
async def handle_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Recebida mensagem: {update.message.text}")
    print(f"Estado do contexto: {context.user_data}")
    
    if context.user_data.get('criando_caso'):
        await handle_caso_message(update, context)
    elif context.user_data.get('editando') and context.user_data.get('caso_selecionado'):
        from casos import handle_caso_edicao_message
        await handle_caso_edicao_message(update, context)
    elif context.user_data.get('esperando_documento'):
        print("Processando documento")
        await texto_handler(update, context)
    elif context.user_data.get('esperando_id_dpc'):
        print("Processando ID do DPC")
        await processar_id_dpc(update, context)
    elif context.user_data.get('criando_lembrete'):
        print("Processando lembrete")
        await handle_lembrete_message(update, context)
    elif context.user_data.get('criando_contato') or context.user_data.get('pesquisando_contato'):
        print("Processando contato")
        await handle_contato_message(update, context)
    elif context.user_data.get('envio_mensagem', {}).get('aguardando_texto'):
        print("Processando envio de mensagem")
        await processar_mensagem(update, context)

def main():
    print("🚀 Iniciando o bot...")
    
    # Configurar timezone no PostgreSQL
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SET TIME ZONE 'America/Sao_Paulo'")
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    # Criar todas as tabelas necessárias
    criar_tabela_usuarios(ADMIN_ID)
    atualizar_nome_admin(ADMIN_ID)
    criar_tabela()
    criar_tabela_lembretes()
    criar_tabela_acessos()
    criar_todas_tabelas()
    criar_tabela_estatisticas()
    criar_tabela_contatos()
    criar_tabela_casos() 
    
    # Criar tabelas específicas
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
        
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    
    application = Application.builder().token(TOKEN).build()
    
    job_queue = application.job_queue
    job_queue.run_repeating(verificar_lembretes, interval=60)

    # Comandos básicos
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('ajuda', comando_ajuda))
    application.add_handler(CommandHandler('help', comando_ajuda))
    application.add_handler(CommandHandler('admin07', menu_admin))
    
    # Handlers principais
    application.add_handler(CallbackQueryHandler(button_handler_main))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mensagem))
    
    # Comandos de atalho
    application.add_handler(CommandHandler('assinaturas', assinaturas_command))
    application.add_handler(CommandHandler('casos', casos_command))
    application.add_handler(CommandHandler('contatos', contatos_command))
    application.add_handler(CommandHandler('lembretes', lembretes_command))
    application.add_handler(CommandHandler('stats', stats_command))
    application.add_handler(CommandHandler('cancel', cancelar_operacao))

    application.run_polling()

if __name__ == '__main__':
    main()
