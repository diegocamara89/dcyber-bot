import pytz
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from database import (
    is_admin, 
    listar_usuarios, 
    alterar_nivel_usuario, 
    get_db_connection,
    adicionar_usuario,
    obter_relatorio_atividades,
    listar_usuarios_pendentes,
    listar_usuarios_ativos,
    aprovar_usuario,
    recusar_usuario,
    desativar_usuario,
    get_user_display_info
)
from decorators import admin_required

# Configuração global do timezone
TIMEZONE = pytz.timezone('America/Sao_Paulo')

@admin_required  # Adicione este decorador
async def menu_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal de administração"""
    keyboard = [
        [InlineKeyboardButton("👥 Gerenciar Usuários", callback_data='admin_usuarios')],
        [InlineKeyboardButton("📊 Relatórios", callback_data='admin_relatorios')],
        [InlineKeyboardButton("⚙️ Configurações", callback_data='admin_config')],
        [InlineKeyboardButton("🔙 Voltar", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text="👑 Menu Administrativo",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text="👑 Menu Administrativo",
            reply_markup=reply_markup
        )

async def menu_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu de gerenciamento de usuários"""
    usuarios_pendentes = listar_usuarios_pendentes()
    total_pendentes = len(usuarios_pendentes)
    
    keyboard = [
        [InlineKeyboardButton(f"✅ Aprovar Usuários ({total_pendentes})", callback_data='admin_aprovar_usuarios')],
        [InlineKeyboardButton("👥 Gerenciar Usuários", callback_data='admin_gerenciar_usuarios')],
        [InlineKeyboardButton("🔰 Definir DPC", callback_data='definir_dpc')],
        [InlineKeyboardButton("📨 Enviar Mensagem", callback_data='admin_enviar_mensagem')],
        [InlineKeyboardButton("🔙 Voltar", callback_data='menu_admin')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="👥 Gestão de Usuários",
        reply_markup=reply_markup
    )
    
async def menu_gerenciar_usuario_individual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu de gerenciamento de um usuário específico"""
    query = update.callback_query
    user_id = int(query.data.split('_')[-1])
    user_info = get_user_display_info(user_id)
    
    if not user_info:
        await query.answer("❌ Usuário não encontrado")
        return
    
    texto = f"⚙️ *Gerenciar Usuário*\n\n"
    texto += f"👤 Nome: {user_info['nome_completo']}\n"
    texto += f"🆔 ID: `{user_info['user_id']}`\n"
    texto += f"📝 Username: @{user_info['username'] if user_info['username'] else 'Não informado'}\n"
    texto += f"🔰 Nível: {user_info['nivel']}\n"
    texto += f"📊 Status: {'✅ Ativo' if user_info['ativo'] else '❌ Inativo'}\n"
    
    keyboard = [
        # Botões de nível
        [InlineKeyboardButton("👑 Admin", callback_data=f'set_nivel_admin_{user_id}'),
         InlineKeyboardButton("🔰 DPC", callback_data=f'set_nivel_dpc_{user_id}')],
        [InlineKeyboardButton("👤 Usuário", callback_data=f'set_nivel_user_{user_id}')],
        
        # Botões de status
        [InlineKeyboardButton("✅ Ativar", callback_data=f'set_status_ativo_{user_id}'),
         InlineKeyboardButton("❌ Desativar", callback_data=f'set_status_inativo_{user_id}')],
        
        # Outras opções
        [InlineKeyboardButton("📨 Enviar Mensagem", callback_data=f'enviar_msg_{user_id}')],
        [InlineKeyboardButton("🔙 Voltar", callback_data='admin_gerenciar_usuarios')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        texto,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# Sistema de mensagens
async def iniciar_envio_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o processo de envio de mensagem para usuários"""
    usuarios = listar_usuarios_ativos()
    texto = "📨 *Enviar Mensagem*\n\n"
    texto += "Selecione para quem deseja enviar a mensagem:\n\n"
    
    keyboard = []
    keyboard.append([InlineKeyboardButton("📢 Todos os Usuários", callback_data='msg_todos')])
    keyboard.append([InlineKeyboardButton("👥 Todos os Usuários Comuns", callback_data='msg_nivel_user')])
    keyboard.append([InlineKeyboardButton("🔰 Apenas DPC", callback_data='msg_nivel_dpc')])
    
    for usuario in usuarios:
        if usuario['user_id'] != update.effective_user.id:  # Não mostrar o próprio usuário
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {usuario['nome']}", 
                    callback_data=f'msg_user_{usuario["user_id"]}'
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='admin_usuarios')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        texto,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def solicitar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicita o texto da mensagem a ser enviada"""
    query = update.callback_query
    destino = query.data.split('_', 1)[1]  # msg_todos, msg_nivel_xxx, msg_user_xxx
    
    context.user_data['envio_mensagem'] = {
        'destino': destino,
        'aguardando_texto': True
    }
    
    texto = (
        "📝 *Digite a mensagem que deseja enviar*\n\n"
        "A mensagem será enviada exatamente como você digitar.\n"
        "Você pode usar formatação Markdown:\n"
        "• *texto* para negrito\n"
        "• _texto_ para itálico\n"
        "• `texto` para monospace\n\n"
        "Use /cancel para cancelar o envio."
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data='cancelar_envio')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        texto,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa e envia a mensagem para os destinatários"""
    if not context.user_data.get('envio_mensagem', {}).get('aguardando_texto'):
        return
    
    mensagem = update.message.text
    destino = context.user_data['envio_mensagem']['destino']
    
    try:
        enviados = 0
        falhas = 0
        usuarios = []
        
        print(f"Processando mensagem para destino: {destino}")
        
        if destino == 'todos':
            usuarios = listar_usuarios_ativos()
        elif destino.startswith('nivel_'):
            nivel = destino.split('_')[1]
            usuarios = [u for u in listar_usuarios_ativos() if u['nivel'] == nivel]
        elif destino.startswith('user_'):
            user_id = int(destino.split('_')[1])
            user_info = get_user_display_info(user_id=user_id)
            if user_info:
                usuarios = [user_info]
            print(f"Usuário específico: {user_info}")
        
        print(f"Total de destinatários: {len(usuarios)}")
        
        for usuario in usuarios:
            try:
                user_id = usuario['user_id']
                print(f"Tentando enviar para usuário ID: {user_id}")
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"{mensagem}",
                    parse_mode='Markdown'
                )
                enviados += 1
                print(f"Mensagem enviada com sucesso para {user_id}")
            except Exception as e:
                print(f"Erro ao enviar mensagem para {usuario.get('nome', 'Unknown')}: {e}")
                falhas += 1
        
        # Relatório de envio
        keyboard = [
            [InlineKeyboardButton("📨 Nova Mensagem", callback_data='admin_enviar_mensagem')],
            [InlineKeyboardButton("🔙 Menu Principal", callback_data='menu_principal')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ *Relatório de Envio*\n\n"
            f"📊 Total de destinatários: {len(usuarios)}\n"
            f"✓ Mensagens enviadas: {enviados}\n"
            f"❌ Falhas no envio: {falhas}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"Erro ao processar mensagem: {str(e)}")
        await update.message.reply_text(f"❌ Erro ao enviar mensagens: {str(e)}")
    finally:
        context.user_data.pop('envio_mensagem', None)

async def menu_aprovar_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu para aprovação de usuários pendentes"""
    usuarios_pendentes = listar_usuarios_pendentes()
    
    if not usuarios_pendentes:
        keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='menu_admin')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text="✅ Não há usuários pendentes de aprovação.",
            reply_markup=reply_markup
        )
        return

    texto = "👥 Usuários Pendentes de Aprovação:\n\n"
    keyboard = []
    
    for usuario in usuarios_pendentes:
        texto += f"• Nome: {usuario['nome']}\n"
        texto += f"  ID: {usuario['user_id']}\n"
        texto += f"  Username: @{usuario['username'] if usuario['username'] else 'Não informado'}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"✅ Aprovar {usuario['nome']}", 
                callback_data=f'admin_aprovar_{usuario["user_id"]}'
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                f"❌ Recusar {usuario['nome']}", 
                callback_data=f'admin_recusar_{usuario["user_id"]}'
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='menu_admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=texto,
        reply_markup=reply_markup
    )

async def menu_relatorios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu de relatórios"""
    keyboard = [
        [InlineKeyboardButton("📊 Relatório de Hoje", callback_data='relatorio_hoje')],
        [InlineKeyboardButton("📅 Últimos 7 dias", callback_data='relatorio_semana')],
        [InlineKeyboardButton("📆 Este Mês", callback_data='relatorio_mes')],
        [InlineKeyboardButton("📈 Mês Anterior", callback_data='relatorio_mes_anterior')],
        [InlineKeyboardButton("🔙 Menu Admin", callback_data='menu_admin')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "📊 *Menu de Relatórios*\n\nEscolha o período:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def menu_configuracoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu de configurações"""
    keyboard = [
        [InlineKeyboardButton("⚙️ Configurações Gerais", callback_data='config_gerais')],
        [InlineKeyboardButton("🔙 Menu Admin", callback_data='menu_admin')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "⚙️ *Configurações do Sistema*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def solicitar_id_dpc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicita o ID do novo DPC"""
    texto = ("🔰 *Definir novo DPC*\n\n"
             "Digite o ID do usuário que você deseja definir como DPC.\n"
             "Exemplo: `123456789`")
    
    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='admin_usuarios')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    print("Solicitando ID do DPC")
    context.user_data['esperando_id_dpc'] = True
    await update.callback_query.edit_message_text(
        texto, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )

async def processar_id_dpc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o ID do DPC recebido"""
    if not context.user_data.get('esperando_id_dpc'):
        return
    
    try:
        novo_dpc_id = int(update.message.text)
        if alterar_nivel_usuario(novo_dpc_id, 'dpc'):
            keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='admin_usuarios')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"✅ Usuário ID: {novo_dpc_id} foi definido como DPC com sucesso!",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Erro ao definir o DPC. Verifique o ID e tente novamente.")
    
    except ValueError:
        await update.message.reply_text("❌ Por favor, envie apenas números para o ID.")
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
        await update.message.reply_text(f"❌ Erro inesperado: {str(e)}")
    finally:
        context.user_data['esperando_id_dpc'] = False

@admin_required
async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler principal para callbacks administrativos"""
    query = update.callback_query
    print(f"handle_admin_callback recebeu: {query.data}")
    
    await query.answer()
    
    try:
        if query.data == 'admin_usuarios':
            await menu_usuarios(update, context)
        
        elif query.data == 'admin_aprovar_usuarios':
            await menu_aprovar_usuarios(update, context)
        
        elif query.data == 'admin_gerenciar_usuarios':
            usuarios = listar_usuarios()
            texto = "👥 *Lista de Usuários*\n\n"
            keyboard = []
            
            for user in usuarios:
                user_id, nome, username, nivel, data_cadastro = user
                if nivel != 'admin':  # Não permite gerenciar administradores
                    nivel_emoji = {
                        'dpc': '🔰',
                        'user': '👤',
                        'pendente': '⏳'
                    }.get(nivel, '❓')
                    
                    texto += f"{nivel_emoji} *{nome}*\n"
                    texto += f"├ ID: `{user_id}`\n"
                    texto += f"├ Username: @{username if username else 'Não informado'}\n"
                    texto += f"├ Nível: {nivel}\n\n"
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"⚙️ Gerenciar {nome}", 
                            callback_data=f'gerenciar_usuario_{user_id}'
                        )
                    ])
            
            keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='admin_usuarios')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=texto,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        elif query.data.startswith('admin_aprovar_'):
            user_id = int(query.data.replace('admin_aprovar_', ''))
            if aprovar_usuario(user_id):
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="✅ Seu acesso foi aprovado! Você já pode utilizar todas as funcionalidades do bot."
                    )
                except Exception as e:
                    print(f"Erro ao notificar usuário aprovado: {e}")
                await menu_aprovar_usuarios(update, context)
            else:
                await query.answer("❌ Erro ao aprovar usuário")
        
        elif query.data.startswith('admin_recusar_'):
            user_id = int(query.data.replace('admin_recusar_', ''))
            if recusar_usuario(user_id):
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="❌ Seu acesso não foi aprovado. Entre em contato com o administrador para mais informações."
                    )
                except Exception as e:
                    print(f"Erro ao notificar usuário recusado: {e}")
                await menu_aprovar_usuarios(update, context)
            else:
                await query.answer("❌ Erro ao recusar usuário")
        
        elif query.data == 'admin_relatorios':
            await menu_relatorios(update, context)
        
        elif query.data == 'admin_config':
            await menu_configuracoes(update, context)
        
        elif query.data == 'definir_dpc':
            await solicitar_id_dpc(update, context)
        
        elif query.data == 'menu_admin':
            await menu_admin(update, context)
        
        elif query.data == 'menu_relatorios':
            await menu_relatorios(update, context)
        
        elif query.data == 'admin_enviar_mensagem':
            await iniciar_envio_mensagem(update, context)
        
        elif query.data.startswith('gerenciar_usuario_'):  # Nova condição adicionada
            await menu_gerenciar_usuario_individual(update, context)
            
        elif query.data.startswith('msg_'):
            await solicitar_mensagem(update, context)
        
        elif query.data == 'cancelar_envio':
            context.user_data.pop('envio_mensagem', None)
            await menu_usuarios(update, context)
        
        elif query.data.startswith('set_nivel_'):
            try:
                # Exemplo de callback: set_nivel_user_123456789
                partes = query.data.split('_')
                if len(partes) >= 4:
                    nivel = partes[2]
                    user_id = partes[3]
                    
                    if alterar_nivel_usuario(int(user_id), nivel):
                        await query.answer(f"✅ Nível alterado para {nivel}")
                        await query.edit_message_text(
                            "✅ Nível alterado com sucesso!\nVoltando para a lista de usuários...",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔄 Atualizar Lista", callback_data='admin_gerenciar_usuarios')
                            ]])
                        )
                    else:
                        await query.answer("❌ Erro ao alterar nível")
                else:
                    await query.answer("❌ Formato de callback inválido")
            except Exception as e:
                print(f"Erro ao processar alteração de nível: {e}")
              await query.answer("❌ Erro ao processar alteração de nível")
        
        elif query.data.startswith('set_status_'):
            _, status, user_id = query.data.split('_')
            user_id = int(user_id)
            if status == 'ativo':
                sucesso = aprovar_usuario(user_id)
            else:
                sucesso = desativar_usuario(user_id)
            
            if sucesso:
                try:
                    if status != 'ativo':
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="❌ Seu acesso foi revogado. Você precisará solicitar nova aprovação para usar o bot."
                        )
                except Exception as e:
                    print(f"Erro ao notificar usuário: {e}")
                
                await query.answer(f"✅ Status alterado com sucesso")
                await query.edit_message_text(
                    "✅ Operação realizada com sucesso!\nVoltando para a lista de usuários...",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Atualizar Lista", callback_data='admin_gerenciar_usuarios')
                    ]])
                )
            else:
                await query.answer("❌ Erro ao alterar status")
        
        elif query.data == 'relatorio_hoje':
            hoje = datetime.now()
            inicio = hoje.replace(hour=0, minute=0, second=0)
            fim = hoje.replace(hour=23, minute=59, second=59)
            await gerar_relatorio(update, context, inicio, fim, "Hoje")

        elif query.data == 'relatorio_semana':
            hoje = datetime.now()
            inicio = hoje - timedelta(days=7)
            fim = hoje
            await gerar_relatorio(update, context, inicio, fim, "Últimos 7 dias")

        elif query.data == 'relatorio_mes':
            hoje = datetime.now()
            inicio = hoje.replace(day=1)
            fim = hoje
            await gerar_relatorio(update, context, inicio, fim, "Este mês")

        elif query.data == 'relatorio_mes_anterior':
            hoje = datetime.now()
            inicio = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
            fim = hoje.replace(day=1) - timedelta(days=1)
            await gerar_relatorio(update, context, inicio, fim, "Mês anterior")

    except Exception as e:
        print(f"Erro no callback administrativo: {e}")
        await query.answer("❌ Erro ao processar comando")


async def gerar_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE, inicio, fim, periodo):
    """Gera relatório detalhado de atividades"""
    try:
        # Ajustar timezone das datas de início e fim
        timezone = pytz.timezone('America/Sao_Paulo')
        inicio = timezone.localize(inicio)
        fim = timezone.localize(fim)

        acessos, assinaturas = obter_relatorio_atividades(inicio, fim)

        texto = f"📊 *Relatório de Atividades - {periodo}*\n\n"

        # Contadores
        total_acessos = 0
        total_assinaturas = 0
        usuarios_ativos = set()

        if acessos:
            texto += "*👥 Acessos ao Sistema*\n"
            for nome, nivel, data, primeiro_acesso, ultimo_acesso, total in acessos:
                total_acessos += total
                usuarios_ativos.add(nome)
                texto += f"• {nome} ({nivel})\n"
                # Converter horários para timezone local
                primeiro_acesso = primeiro_acesso.astimezone(timezone)
                ultimo_acesso = ultimo_acesso.astimezone(timezone)
                texto += f"  └ Primeiro acesso: {primeiro_acesso.strftime('%H:%M')}\n"
                texto += f"  └ Último acesso: {ultimo_acesso.strftime('%H:%M')}\n"
                texto += f"  └ Total de acessos: {total}\n\n"

        if assinaturas:
            texto += "*📝 Assinaturas Processadas*\n"
            for nome, data, total in assinaturas:
                total_assinaturas += total
                texto += f"• {nome}: {total} assinaturas\n"

        # Resumo
        texto += "\n*📈 Resumo do Período*\n"
        texto += f"• Total de acessos: {total_acessos}\n"
        texto += f"• Usuários ativos: {len(usuarios_ativos)}\n"
        texto += f"• Assinaturas processadas: {total_assinaturas}\n"

        if not acessos and not assinaturas:
            texto += "\nNenhuma atividade registrada no período."

        keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='admin_relatorios')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            texto,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
        await update.callback_query.answer("❌ Erro ao gerar relatório")
