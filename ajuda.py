# ajuda.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from decorators import user_approved
import sqlite3

# Textos de ajuda
AJUDA_GERAL = """
*🤖 Bem-vindo à Ajuda do Dcyber Bot!*

*Comandos Disponíveis:*
/start - Inicia o bot
/ajuda - Mostra esta mensagem
/assinaturas - Menu de assinaturas
/casos - Menu de casos
/contatos - Menu de contatos
/lembretes - Menu de lembretes
/stats - Estatísticas

*Dicas Rápidas:*
• Use o menu principal para navegar
• Clique nos botões 🔙 para voltar
• Use /cancel para cancelar operações

*Precisa de ajuda específica?*
Selecione um tópico abaixo 👇
"""

AJUDA_ASSINATURAS = """
*📑 Ajuda - Assinaturas*

*Como solicitar uma assinatura:*
1. Acesse o menu Assinaturas
2. Clique em "Solicitar Assinatura"
3. Digite o texto do documento
4. Aguarde a aprovação do DPC

*Dicas:*
• Você pode enviar vários documentos
• Separe cada documento em uma linha
• Aguarde a notificação de aprovação

*Comandos úteis:*
/assinaturas - Abre o menu
/consultar - Consulta suas assinaturas
"""

AJUDA_CASOS = """
*📁 Ajuda - Casos*

*Como criar um novo caso:*
1. Acesse o menu Casos
2. Clique em "Novo Caso"
3. Siga as instruções na tela
4. Adicione responsáveis

*Dicas:*
• Mantenha o status atualizado
• Adicione observações relevantes
• Você pode editar casos existentes

*Comandos úteis:*
/casos - Abre o menu
/novocaso - Cria novo caso
/meuscasos - Lista seus casos
"""

AJUDA_CONTATOS = """
*📇 Ajuda - Contatos*

*Como adicionar contatos:*
1. Acesse menu Contatos
2. Clique em "Novo Contato"
3. Digite as informações
4. Confirme o cadastro

*Formato do contato:*
Nome
Telefone/Email
Observações (opcional)

*Comandos úteis:*
/contatos - Abre o menu
/novocontato - Adiciona contato
/buscar - Pesquisa contatos
"""

AJUDA_LEMBRETES = """
*⏰ Ajuda - Lembretes*

*Como criar lembretes:*
1. Acesse menu Lembretes
2. Clique em "Novo Lembrete"
3. Digite título e data/hora
4. Selecione destinatários

*Dicas:*
• Use formato DD/MM/YYYY
• Horário em 24h (HH:MM)
• Você receberá notificações

*Comandos úteis:*
/lembretes - Abre o menu
/novolembrete - Cria lembrete
/meuslembretes - Lista lembretes
"""

@user_approved
async def menu_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal de ajuda"""
    keyboard = [
        [InlineKeyboardButton("📑 Assinaturas", callback_data='ajuda_assinaturas')],
        [InlineKeyboardButton("📁 Casos", callback_data='ajuda_casos')],
        [InlineKeyboardButton("📇 Contatos", callback_data='ajuda_contatos')],
        [InlineKeyboardButton("⏰ Lembretes", callback_data='ajuda_lembretes')],
        [InlineKeyboardButton("🔙 Voltar", callback_data='menu_principal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            AJUDA_GERAL,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            AJUDA_GERAL,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

async def comando_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ajuda"""
    await menu_ajuda(update, context)

@user_approved
async def handle_ajuda_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia callbacks do menu de ajuda"""
    query = update.callback_query
    await query.answer()
    
    ajuda_textos = {
        'ajuda_assinaturas': AJUDA_ASSINATURAS,
        'ajuda_casos': AJUDA_CASOS,
        'ajuda_contatos': AJUDA_CONTATOS,
        'ajuda_lembretes': AJUDA_LEMBRETES
    }
    
    if query.data in ajuda_textos:
        keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='ajuda')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            ajuda_textos[query.data],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == 'ajuda':
        await menu_ajuda(update, context)