from telegram import Update
from telegram.ext import ContextTypes
from auth import is_admin, is_user_approved

def admin_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def user_approved(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Se for admin, permite acesso
        if is_admin(user_id):
            return await func(update, context, *args, **kwargs)
        
        # Verifica se usuário está ativo
        if not is_user_approved(user_id):
            if hasattr(update, 'callback_query'):
                await update.callback_query.answer("⚠️ Aguardando aprovação do administrador")
                return
            else:
                await update.message.reply_text(
                    "⚠️ Seu acesso ainda não foi aprovado.\n"
                    "Por favor, aguarde a aprovação do administrador."
                )
                return
        
        return await func(update, context, *args, **kwargs)
    return wrapper