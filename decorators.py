from functools import wraps
from telegram import Update
from telegram.constants import ParseMode
from auth import is_admin, is_user_active

def admin_required(func):
    @wraps(func)
    async def wrapper(update: Update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if is_admin(user_id):
            return await func(update, context, *args, **kwargs)
        else:
            if update.callback_query:
                await update.callback_query.answer("❌ Acesso negado")
            else:
                await update.message.reply_text(
                    "❌ Apenas administradores podem usar este comando.",
                    parse_mode=ParseMode.MARKDOWN
                )
            return None
    return wrapper

def user_approved(func):
    @wraps(func)
    async def wrapper(update: Update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if is_admin(user_id) or is_user_active(user_id):
            return await func(update, context, *args, **kwargs)
        else:
            if update.callback_query:
                await update.callback_query.answer("❌ Acesso pendente")
                await update.callback_query.message.reply_text(
                    "⚠️ Seu acesso ainda está pendente de aprovação.\n"
                    "Por favor, aguarde a aprovação do administrador.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    "⚠️ Seu acesso ainda está pendente de aprovação.\n"
                    "Por favor, aguarde a aprovação do administrador.",
                    parse_mode=ParseMode.MARKDOWN
                )
            return None
    return wrapper
