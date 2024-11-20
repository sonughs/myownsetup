import logging
import random
import requests
import ipaddress
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler, filters

# Logging Configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Constants
ADMIN_USER_ID = '1119536718'
ADMIN_USERNAME = '@SonuGamingOp'
BOT_TOKEN = '7731725265:AAEpnW5ak-Qca-uJdSxyjszDwnc4Fmo0NVw'
DEFAULT_DOMAIN = 'sonugamingop.tech'
AVAILABLE_DOMAINS = [DEFAULT_DOMAIN]
RESERVED_DOMAINS = ['example.com', 'private.net']
user_subdomains = {}

cloudflare_configs = {
    'sonugamingop.tech': {
        'api_key': 'K3ipUGciOujIW1Dqt8PN2q1OKJF0j9ZQIil4wLVJ',
        'zone_id': 'd3eeb9111615f912bfb3f49b2395e461',
        'email': 'sonusinghghs@gmail.com'
    }
}

# Steps for Conversation
(ASK_SUBDOMAIN, ASK_IP) = range(2)

PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16')
]

# Helper Functions
def is_private_ip(ip: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
        return any(ip_obj in network for network in PRIVATE_IP_RANGES)
    except ValueError:
        return False

async def typing_indicator(context: CallbackContext, chat_id: int):
    """Simulate typing for better user experience."""
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

# Bot Commands
async def start(update: Update, context: CallbackContext) -> None:
    """Display a professional welcome message with a structured menu."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("➕ Add New Subdomain", callback_data='adddomain')],
        [InlineKeyboardButton("🗑️ Manage Subdomains", callback_data='cleardomain')],
        [InlineKeyboardButton("ℹ️ Help & Support", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(
        rf"""
<b>Welcome, {user.mention_html()}! 👋</b>

🎯 <u>What would you like to do?</u>
- Manage subdomains for your custom domains.
- Get real-time support.

Use the menu below to proceed! 👇
        """,
        reply_markup=reply_markup
    )

async def ask_subdomain_name(update: Update, context: CallbackContext) -> int:
    """Prompt the user to provide their desired subdomain name."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="📝 <b>Enter your desired subdomain name and IP address in the format:</b>\n\n"
             "<code>subdomain_name IP_address</code>\n\n"
             "⚠️ Ensure that the subdomain name is unique!",
        parse_mode="HTML"
    )
    return ASK_SUBDOMAIN

async def adddomain(update: Update, context: CallbackContext) -> int:
    """Add a custom subdomain with professional feedback."""
    user = update.effective_user
    user_id = user.id
    chat_id = update.message.chat_id
    await typing_indicator(context, chat_id)

    # Extract user input
    message_parts = update.message.text.split()
    if len(message_parts) < 2:
        await update.message.reply_text("❌ Invalid format. Use:\n<code>subdomain_name IP_address</code>", parse_mode="HTML")
        return ASK_SUBDOMAIN

    subdomain_name, ip_address = message_parts[0], message_parts[1]
    full_subdomain = f"{subdomain_name}.{DEFAULT_DOMAIN}"

    if is_private_ip(ip_address):
        await update.message.reply_text("❌ Private IP addresses are not allowed.")
        return ConversationHandler.END

    if user_id not in user_subdomains:
        user_subdomains[user_id] = []

    if len(user_subdomains[user_id]) < 5:
        cloudflare_info = cloudflare_configs.get(DEFAULT_DOMAIN)
        if not cloudflare_info:
            await update.message.reply_text("⚠️ Cloudflare configuration missing. Contact admin.")
            return ConversationHandler.END

        # Add Subdomain
        user_subdomains[user_id].append({'subdomain': full_subdomain, 'ip': ip_address})
        await update.message.reply_html(
            f"✅ <b>Subdomain Created!</b>\n\n"
            f"👤 <b>Admin:</b> @{ADMIN_USERNAME}\n"
            f"🌐 <b>Subdomain:</b> {full_subdomain}\n"
            f"📍 <b>IP Address:</b> {ip_address}\n\n"
            f"💬 <i>If you encounter any issues, contact admin.</i>"
        )
    else:
        await update.message.reply_text("⚠️ Limit of 5 subdomains reached. Clear old subdomains first.")
    return ConversationHandler.END

async def help_command(update: Update, context: CallbackContext) -> None:
    """Provide a detailed help message with links."""
    keyboard = [
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(
        text=(
            "ℹ️ <b>Help & Support</b>\n\n"
            "👨‍💻 Need assistance? Contact the admin directly using the button below.\n"
            "📖 Refer to the user manual for detailed instructions.\n"
            "💡 Suggestions are always welcome!"
        ),
        reply_markup=reply_markup
    )

# Main Function
def main() -> None:
    """Run the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_subdomain_name, pattern='^adddomain$')],
        states={ASK_SUBDOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, adddomain)]},
        fallbacks=[]
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(help_command, pattern='^help$'))
    application.run_polling()

if __name__ == '__main__':
    main()
