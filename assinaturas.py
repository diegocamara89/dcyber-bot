# assinaturas.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import (
    consultar_assinaturas, 
    apagar_assinatura_por_sequencia, 
    gerar_sequencia, 
    inserir_assinatura,
    obter_id_dpc,
    registrar_acesso,
    get_user_display_info
)
from database_estatisticas import incrementar_contador, registrar_acao_usuario
from decorators import user_approved, admin_required

async def create_admin_notification_markup(sequencia):
    """Cria markup para notificação do admin/DPC"""
    keyboard = [
        [InlineKeyboardButton("✍️ Assinar", callback_data=f'assinar_notificacao_{sequencia}')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def atualizar_menu_assinaturas(query, context):
    """Atualiza o menu de assinaturas com as pendentes"""
    assinaturas = consultar_assinaturas()
    if not assinaturas:
        await query.edit_message_text(
            text="📝 *Assinaturas Pendentes*\n\n"
                 "ℹ️ Nenhuma assinatura pendente no momento.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Voltar", callback_data='assinaturas')
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Limitar a 5 assinaturas por vez
    assinaturas = assinaturas[:5]
    assinaturas_texto = "*📋 Assinaturas Pendentes:*\n\n"
    
    for _, _, username, documento, seq in assinaturas:
        user_info = get_user_display_info(username=username)
        display_name = user_info['display_name'] if user_info else username
        assinaturas_texto += f"📄 *#{seq}*\n"
        assinaturas_texto += f"👤 Solicitante: {display_name}\n"
        assinaturas_texto += f"📝 Documento: {documento}\n\n"
    
    keyboard = []
    for _, _, _, _, seq in assinaturas:
        keyboard.append([
            InlineKeyboardButton(f"✍️ Assinar #{seq}", callback_data=f'assinar_lista_{seq}')
        ])
    
    keyboard.append([InlineKeyboardButton("✍️ Assinar Todas", callback_data='apagar_todas_assinaturas')])
    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data='assinaturas')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=assinaturas_texto,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

@user_approved
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler principal para botões de assinaturas"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'assinaturas':
        keyboard = [
            [InlineKeyboardButton("✍️ Solicitar Assinatura", callback_data='solicitar_assinatura')],
            [InlineKeyboardButton("🔍 Consultar Assinatura", callback_data='consultar_assinatura')],
            [InlineKeyboardButton("🔙 Voltar", callback_data='menu_principal')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="📑 *Menu de Assinaturas*\n\n"
                 "Escolha uma opção:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    elif query.data == 'solicitar_assinatura':
        registrar_acesso(user_id, 'solicitacao_assinatura')
        dpc_id = obter_id_dpc()
        if not dpc_id:
            await query.edit_message_text(
                text="⚠️ *Atenção!*\n\n"
                     "Não há DPC definido no sistema.\n"
                     "Por favor, contate o administrador.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='assinaturas')
                ]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        await query.edit_message_text(
            text="📝 *Nova Solicitação de Assinatura*\n\n"
                 "Envie os documentos que deseja cadastrar para assinatura.\n\n"
                 "*Dicas:*\n"
                 "• Separe cada documento em uma linha\n"
                 "• Seja claro e objetivo\n"
                 "• Evite caracteres especiais",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Voltar", callback_data='assinaturas')
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['esperando_documento'] = True

    elif query.data == 'consultar_assinatura':
        await atualizar_menu_assinaturas(query, context)

    elif query.data.startswith('assinar_notificacao_'):
        sequencia = int(query.data.split('_')[-1])
        user_info = apagar_assinatura_por_sequencia(sequencia)
        if user_info:
            user_id, username, documento = user_info
            solicitante_info = get_user_display_info(user_id=user_id)
            display_name = solicitante_info['display_name'] if solicitante_info else username
            
            # Notifica o usuário que cadastrou a assinatura
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *Documento Assinado!*\n\n"
                     f"📝 Documento: {documento}\n"
                     f"👤 Solicitante: {display_name}",
                parse_mode=ParseMode.MARKDOWN
            )
            # Atualiza a mensagem do admin/DPC
            await query.edit_message_text(
                text=f"✅ *Assinatura Confirmada!*\n\n"
                     f"📝 Documento: {documento}\n"
                     f"👤 Solicitante: {display_name}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                text="❌ *Erro*\n\n"
                     "Assinatura não encontrada ou já processada.",
                parse_mode=ParseMode.MARKDOWN
            )

    elif query.data.startswith('assinar_lista_'):
        sequencia = int(query.data.split('_')[-1])
        user_info = apagar_assinatura_por_sequencia(sequencia)
        if user_info:
            user_id, username, documento = user_info
            solicitante_info = get_user_display_info(user_id=user_id)
            display_name = solicitante_info['display_name'] if solicitante_info else username
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *Documento Assinado!*\n\n"
                     f"📝 Documento: {documento}",
                parse_mode=ParseMode.MARKDOWN
            )
            await atualizar_menu_assinaturas(query, context)

    elif query.data == 'apagar_todas_assinaturas':
        assinaturas = consultar_assinaturas()
        if not assinaturas:
            await query.edit_message_text(
                text="ℹ️ *Informação*\n\n"
                     "Nenhuma assinatura pendente para processar.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='assinaturas')
                ]]),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            total_assinadas = 0
            for _, user_id, username, documento, sequencia in assinaturas:
                user_info = apagar_assinatura_por_sequencia(sequencia)
                if user_info:
                    total_assinadas += 1
                    solicitante_info = get_user_display_info(user_id=user_id)
                    display_name = solicitante_info['display_name'] if solicitante_info else username
                    
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ *Documento Assinado!*\n\n"
                             f"📝 Documento: {documento}",
                        parse_mode=ParseMode.MARKDOWN
                    )
            
            await query.edit_message_text(
                text=f"✅ *Processamento Concluído*\n\n"
                     f"Total de documentos assinados: {total_assinadas}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Voltar", callback_data='assinaturas')
                ]]),
                parse_mode=ParseMode.MARKDOWN
            )

    elif query.data == 'menu_principal':
        from dcyber_bot import start
        await start(update, context)

def adicionar_assinatura(user_id, username, documento):
    """Adiciona nova assinatura no sistema"""
    try:
        sequencia = gerar_sequencia()
        if inserir_assinatura(user_id, username, documento, sequencia):
            incrementar_contador('documentos')
            registrar_acao_usuario(user_id, 'novo_documento')
            print(f"Assinatura adicionada - Seq: {sequencia}, User: {username}")
            return sequencia
        return None
    except Exception as e:
        print(f"Erro ao adicionar assinatura: {e}")
        return None