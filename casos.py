# casos.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database_casos import (
    adicionar_caso_db,
    consultar_casos_db,
    atualizar_caso_db,
    encerrar_caso_db,
    criar_tabela_casos
)
from database import get_user_display_info, get_usuarios_cadastrados
from decorators import user_approved, admin_required
from telegram.constants import ParseMode
from database_estatisticas import incrementar_contador, registrar_acao_usuario

@user_approved
async def menu_casos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Novo Caso", callback_data='caso_novo')],
        [InlineKeyboardButton("📋 Listar Casos", callback_data='caso_listar')],
        [InlineKeyboardButton("✏️ Ajustar Casos", callback_data='caso_ajustar')],
        [InlineKeyboardButton("🔙 Voltar", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="📁 Gestão de Casos\n\n"
             "Escolha uma opção:",
        reply_markup=reply_markup
    )

@user_approved
async def criar_caso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['criando_caso'] = True
    context.user_data['etapa_caso'] = 'titulo'
    keyboard = [[InlineKeyboardButton("🔙 Cancelar", callback_data='casos')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="📝 Novo Caso\n\n"
             "Digite o título do caso:",
        reply_markup=reply_markup
    )

@user_approved
async def listar_casos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    casos = consultar_casos_db()
    
    if not casos:
        keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='casos')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text="Nenhum caso registrado.",
            reply_markup=reply_markup
        )
        return

    texto = "📋 Casos em Andamento:\n\n"
    keyboard = []
    
    for caso in casos:
        id_caso, titulo, observacoes, status, responsaveis, data = caso
        texto += f"📎 Título: {titulo}\n"
        texto += f"👥 Responsáveis: {responsaveis}\n"
        texto += f"📊 Status: {status}\n"
        if observacoes:
            texto += f"📝 Observações: {observacoes}\n"
        texto += "\n"
    
    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='casos')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=texto,
        reply_markup=reply_markup
    )

@user_approved
async def listar_casos_ajuste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    casos = consultar_casos_db()
    
    if not casos:
        keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='casos')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text="Nenhum caso registrado.",
            reply_markup=reply_markup
        )
        return

    keyboard = []
    for caso in casos:
        id_caso, titulo, _, status, _, _ = caso
        keyboard.append([
            InlineKeyboardButton(f"✏️ {titulo} ({status})", callback_data=f'caso_editar_{id_caso}')
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='casos')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="✏️ Selecione um caso para ajustar:",
        reply_markup=reply_markup
    )

@user_approved
async def handle_caso_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('criando_caso'):
        try:
            if not 'caso_titulo' in context.user_data:
                context.user_data['caso_titulo'] = update.message.text.strip()
                await update.message.reply_text(
                    "📝 *Digite a descrição do caso:*\n\n"
                    "Seja o mais detalhado possível.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            elif not 'caso_descricao' in context.user_data:
                context.user_data['caso_descricao'] = update.message.text.strip()
                await update.message.reply_text(
                    "📝 *Digite as observações (opcional):*\n\n"
                    "Use /pular se não quiser adicionar observações.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            elif not 'caso_observacoes' in context.user_data:
                if update.message.text == '/pular':
                    context.user_data['caso_observacoes'] = None
                else:
                    context.user_data['caso_observacoes'] = update.message.text.strip()
                
                # Criar o caso
                try:
                    caso_id = adicionar_caso_db(
                        user_id=update.effective_user.id,
                        titulo=context.user_data['caso_titulo'],
                        descricao=context.user_data['caso_descricao'],
                        observacoes=context.user_data['caso_observacoes']
                    )
                    
                    if caso_id:
                        keyboard = [
                            [InlineKeyboardButton("📁 Menu Casos", callback_data='casos')],
                            [InlineKeyboardButton("🏠 Menu Principal", callback_data='menu_principal')]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        texto_resposta = "✅ *Caso criado com sucesso!*\n\n"
                        texto_resposta += f"📌 *Título:* {context.user_data['caso_titulo']}\n"
                        texto_resposta += f"📝 *Descrição:* {context.user_data['caso_descricao']}\n"
                        
                        if context.user_data['caso_observacoes']:
                            texto_resposta += f"\n📋 *Observações:* {context.user_data['caso_observacoes']}"
                        
                        await update.message.reply_text(
                            texto_resposta,
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                        # Registrar estatísticas
                        incrementar_contador('casos')
                        registrar_acao_usuario(update.effective_user.id, 'novo_caso')
                    else:
                        keyboard = [
                            [InlineKeyboardButton("🔄 Tentar Novamente", callback_data='caso_novo')],
                            [InlineKeyboardButton("🔙 Menu Casos", callback_data='casos')]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await update.message.reply_text(
                            "❌ *Erro ao criar caso*\n\n"
                            "Ocorreu um erro ao salvar o caso. Por favor, tente novamente.",
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.MARKDOWN
                        )
                except Exception as e:
                    print(f"Erro ao criar caso no banco: {e}")
                    keyboard = [
                        [InlineKeyboardButton("🔄 Tentar Novamente", callback_data='caso_novo')],
                        [InlineKeyboardButton("🔙 Menu Casos", callback_data='casos')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        "❌ *Erro ao criar caso*\n\n"
                        "Ocorreu um erro no banco de dados. Por favor, tente novamente.",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Limpar dados do contexto
                context.user_data.clear()
                
        except Exception as e:
            print(f"Erro ao criar caso: {e}")
            keyboard = [
                [InlineKeyboardButton("🔄 Tentar Novamente", callback_data='caso_novo')],
                [InlineKeyboardButton("🔙 Menu Casos", callback_data='casos')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ *Erro ao criar caso*\n\n"
                f"Erro: {str(e)}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data.clear()

async def mostrar_selecao_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_user_id = update.effective_user.id
    current_user = get_user_display_info(user_id=current_user_id)
    outros_usuarios = get_usuarios_cadastrados(excluir_user_id=current_user_id)
    
    keyboard = []
    texto = "👥 Selecione os responsáveis:\n(Clique para marcar/desmarcar)"
    responsaveis = context.user_data.get('responsaveis', [])
    
    # Adiciona o usuário atual (se for ativo e não pendente)
    if current_user and current_user.get('nivel') != 'pendente':
        selecionado = str(current_user_id) in responsaveis
        emoji = "✅" if selecionado else "⭕"
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {current_user['display_name']} (Você)",
                callback_data=f'caso_resp_select_{current_user_id}'
            )
        ])
    
    # Adiciona outros usuários
    for user_id, display_name in outros_usuarios:
        selecionado = str(user_id) in responsaveis
        emoji = "✅" if selecionado else "⭕"
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {display_name}",
                callback_data=f'caso_resp_select_{user_id}'
            )
        ])
    
    if responsaveis:
        texto += "\n\n📌 Selecionados:"
        for resp_id in responsaveis:
            user_info = get_user_display_info(user_id=int(resp_id))
            if user_info:
                texto += f"\n• {user_info['display_name']}"
    
    keyboard.append([InlineKeyboardButton("✅ Confirmar", callback_data='caso_resp_confirmar')])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='casos')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update, Update):
        if update.callback_query:
            await update.callback_query.message.edit_text(texto, reply_markup=reply_markup)
        else:
            await update.message.reply_text(texto, reply_markup=reply_markup)

async def handle_caso_edicao_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trata mensagens durante a edição de casos"""
    if 'editando' not in context.user_data:
        return

    texto = update.message.text.strip()
    caso_id = context.user_data.get('caso_selecionado')
    editando = context.user_data.get('editando')

    try:
        if editando == 'status':
            if atualizar_caso_db(caso_id, 'status', texto):
                await update.message.reply_text(
                    "✅ Status atualizado com sucesso!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Voltar", callback_data=f'caso_editar_{caso_id}')
                    ]])
                )
            else:
                await update.message.reply_text(
                    "❌ Erro ao atualizar status",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Voltar", callback_data=f'caso_editar_{caso_id}')
                    ]])
                )
        
        elif editando == 'observacoes':
            observacoes = None if texto == '/pular' else texto
            if atualizar_caso_db(caso_id, 'observacoes', observacoes):
                await update.message.reply_text(
                    "✅ Observações atualizadas com sucesso!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Voltar", callback_data=f'caso_editar_{caso_id}')
                    ]])
                )
            else:
                await update.message.reply_text(
                    "❌ Erro ao atualizar observações",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Voltar", callback_data=f'caso_editar_{caso_id}')
                    ]])
                )
    
    except Exception as e:
        await update.message.reply_text(
            f"❌ Erro ao atualizar caso: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Voltar", callback_data=f'caso_editar_{caso_id}')
            ]])
        )
    finally:
        if 'editando' in context.user_data:
            del context.user_data['editando']

@user_approved
async def handle_casos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'casos':
        await menu_casos(update, context)
    
    elif query.data == 'caso_novo':
        await criar_caso(update, context)
    
    elif query.data == 'caso_listar':
        await listar_casos(update, context)
    
    elif query.data == 'caso_ajustar':
        await listar_casos_ajuste(update, context)
    
    elif query.data.startswith('caso_editar_'):
        caso_id = int(query.data.split('_')[-1])
        context.user_data['caso_selecionado'] = caso_id
        await ajustar_caso(update, context)
    
    elif query.data.startswith('caso_alterar_'):
        await handle_alteracao_callback(update, context)
    
    elif query.data.startswith('caso_resp_'):
        await handle_responsaveis_callback(update, context)
    
    elif query.data == 'menu_principal':
        from dcyber_bot import start
        await start(update, context)
    
    elif query.data == 'pular_observacoes':
        context.user_data['caso_observacoes'] = None
        await finalizar_criacao_caso(update, context)
   
    elif query.data.startswith('caso_encerrar_'):
        caso_id = int(query.data.split('_')[-1])
        if encerrar_caso_db(caso_id):
            await query.edit_message_text(
                "✅ Caso encerrado com sucesso!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='casos')
                ]])
            )
        else:
            await query.edit_message_text(
                "❌ Erro ao encerrar caso",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='casos')
                ]])
            )
    
    elif query.data.startswith('caso_apagar_'):
        caso_id = int(query.data.split('_')[-1])
        # Adicione esta função em database_casos.py
        if apagar_caso_db(caso_id):
            await query.edit_message_text(
                "✅ Caso apagado com sucesso!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='casos')
                ]])
            )
        else:
            await query.edit_message_text(
                "❌ Erro ao apagar caso",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='casos')
                ]])
            )

@user_approved
async def handle_responsaveis_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith('caso_resp_select_'):
        user_id = data.replace('caso_resp_select_', '')
        responsaveis = context.user_data.get('responsaveis', [])
        
        if user_id in responsaveis:
            responsaveis.remove(user_id)
        else:
            responsaveis.append(user_id)
        
        context.user_data['responsaveis'] = responsaveis
        await mostrar_selecao_usuarios(update, context)
    
    elif data == 'caso_resp_confirmar':
        if not context.user_data.get('responsaveis'):
            await query.message.edit_text(
                "⚠️ Selecione pelo menos um responsável!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='caso_resp_selecionar')
                ]])
            )
            return
        
        # Verifica se está editando ou criando caso
        if context.user_data.get('editando'):
            caso_id = context.user_data.get('caso_selecionado')
            if atualizar_caso_db(caso_id, 'responsaveis', context.user_data['responsaveis']):
                await query.message.edit_text(
                    "✅ Responsáveis atualizados com sucesso!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Voltar", callback_data=f'caso_editar_{caso_id}')
                    ]])
                )
            # Limpa o estado de edição
            if 'editando' in context.user_data:
                del context.user_data['editando']
        else:
            # Caso novo, continua para observações
            context.user_data['etapa_caso'] = 'observacoes'
            await query.message.edit_text(
                "📝 Digite as observações do caso:\n"
                "(ou envie /pular para deixar em branco)"
            )
    
    elif data == 'caso_resp_voltar':
        await mostrar_selecao_usuarios(update, context)
            
        keyboard = []
        for _, nome in usuarios:
            selecionado = nome in context.user_data.get('responsaveis', [])
            emoji = "✅" if selecionado else "⭕"
            keyboard.append([
                InlineKeyboardButton(
                    f"{emoji} {nome}",
                    callback_data=f'caso_resp_select_{nome}'
                )
            ])
        
        keyboard.append([InlineKeyboardButton("✅ Confirmar", callback_data='caso_resp_confirmar')])
        keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='caso_resp_voltar')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "👥 Selecione os responsáveis:\n"
            "(Clique para marcar/desmarcar)",
            reply_markup=reply_markup
        )
    
    elif data.startswith('caso_resp_select_'):
        username = data.replace('caso_resp_select_', '')
        responsaveis = context.user_data.get('responsaveis', [])
        
        if username in responsaveis:
            responsaveis.remove(username)
        else:
            responsaveis.append(username)
        
        context.user_data['responsaveis'] = responsaveis
        
        # Atualiza a lista de seleção
        user_id = update.effective_user.id
        usuarios = get_usuarios_cadastrados(excluir_user_id=user_id)
        
        keyboard = []
        for _, nome in usuarios:
            selecionado = nome in responsaveis
            emoji = "✅" if selecionado else "⭕"
            keyboard.append([
                InlineKeyboardButton(
                    f"{emoji} {nome}",
                    callback_data=f'caso_resp_select_{nome}'
                )
            ])
        
        keyboard.append([InlineKeyboardButton("✅ Confirmar", callback_data='caso_resp_confirmar')])
        keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='caso_resp_voltar')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "👥 Selecione os responsáveis:\n"
            "(Clique para marcar/desmarcar)",
            reply_markup=reply_markup
        )
    
    elif data == 'caso_resp_confirmar':
        if not context.user_data.get('responsaveis'):
            await query.message.edit_text(
                "⚠️ Selecione pelo menos um responsável!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='caso_resp_selecionar')
                ]])
            )
            return
        
        context.user_data['etapa_caso'] = 'observacoes'
        await query.message.edit_text(
            "📝 Digite as observações do caso:\n"
            "(ou envie /pular para deixar em branco)"
        )
    
    elif data == 'caso_resp_voltar':
        keyboard = [
            [InlineKeyboardButton("👤 Apenas eu", callback_data='caso_resp_eu')],
            [InlineKeyboardButton("👥 Selecionar usuários", callback_data='caso_resp_selecionar')],
            [InlineKeyboardButton("📢 Todos os usuários", callback_data='caso_resp_todos')],
            [InlineKeyboardButton("🔙 Cancelar", callback_data='casos')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "👥 Quem são os responsáveis por este caso?",
            reply_markup=reply_markup
        )

@user_approved
async def ajustar_caso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caso_id = int(context.user_data.get('caso_selecionado', 0))
    if not caso_id:
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Alterar Status", callback_data=f'caso_alterar_status_{caso_id}')],
        [InlineKeyboardButton("👥 Alterar Responsáveis", callback_data=f'caso_alterar_resp_{caso_id}')],
        [InlineKeyboardButton("📝 Alterar Observações", callback_data=f'caso_alterar_obs_{caso_id}')],
        [InlineKeyboardButton("❌ Encerrar Caso", callback_data=f'caso_encerrar_{caso_id}')],
        [InlineKeyboardButton("🔙 Voltar", callback_data='caso_listar')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="✏️ O que você deseja ajustar?",
        reply_markup=reply_markup
    )

@user_approved
async def handle_alteracao_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    caso_id = context.user_data.get('caso_selecionado')
    
    if not caso_id:
        await query.message.edit_text(
            "❌ Erro: Caso não selecionado",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Voltar", callback_data='casos')
            ]])
        )
        return
    
    if data.startswith('caso_alterar_status_'):
        context.user_data['editando'] = 'status'
        await query.message.edit_text(
            "📊 Digite o novo status do caso:\n\n"
            "Dicas:\n"
            "- Você pode usar emojis\n"
            "- Exemplo: 🟢 Em andamento\n"
            "- Exemplo: ⚠️ Aguardando resposta\n"
            "- Exemplo: ✅ Concluído",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Cancelar", callback_data=f'caso_editar_{caso_id}')
            ]])
        )
    
    elif data.startswith('caso_alterar_obs_'):
        context.user_data['editando'] = 'observacoes'
        await query.message.edit_text(
            "📝 Digite as novas observações do caso:\n"
            "(ou envie /pular para deixar em branco)",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Cancelar", callback_data=f'caso_editar_{caso_id}')
            ]])
        )
    
    elif data.startswith('caso_alterar_resp_'):
        context.user_data['editando'] = 'responsaveis'
        await mostrar_selecao_usuarios(update, context)  # Vai direto para a seleção
    
    elif data.startswith('caso_encerrar_'):
        keyboard = [
            [
                InlineKeyboardButton("✅ Sim", callback_data=f'caso_confirmar_encerrar_{caso_id}'),
                InlineKeyboardButton("❌ Não", callback_data=f'caso_editar_{caso_id}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "⚠️ Tem certeza que deseja encerrar este caso?",
            reply_markup=reply_markup
        )
    
    elif data.startswith('caso_confirmar_encerrar_'):
        if encerrar_caso_db(caso_id):
            await query.message.edit_text(
                "✅ Caso encerrado com sucesso!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='casos')
                ]])
            )
        else:
            await query.message.edit_text(
                "❌ Erro ao encerrar caso",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data=f'caso_editar_{caso_id}')
                ]])
            )
