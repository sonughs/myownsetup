import logging
import random
import string
import requests
import ipaddress
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_USER_ID = '1119536718'
ADMIN_USERNAME = '@SonuGamingOp'
BOT_TOKEN = '7731725265:AAEpnW5ak-Qca-uJdSxyjszDwnc4Fmo0NVw'
DEFAULT_DOMAIN = 'sonugamingop.tech'
available_domains = [DEFAULT_DOMAIN]
user_subdomains = {}
cloudflare_configs = {
    'sonugamingop.tech': {
        'api_key': 'K3ipUGciOujIW1Dqt8PN2q1OKJF0j9ZQIil4wLVJ',
        'zone_id': 'd3eeb9111615f912bfb3f49b2395e461',
        'email': 'sonusinghghs@gmail.com'
    }
}
(ASK_API_KEY, ASK_ZONE_ID, ASK_EMAIL, ASK_DOMAIN, ASK_IP) = range(5)

RESERVED_DOMAINS = ['example.com', 'private.net']  # Add your reserved domains here
PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16')
]
DNS_SERVER_IPS = [
    '8.8.8.8',  # Google DNS
    '8.8.4.4',  # Google DNS
    '1.1.1.1',  # Cloudflare DNS
    '1.0.0.1',  # Cloudflare DNS
    '9.9.9.9',  # Quad9 DNS
    '149.112.112.112'  # Quad9 DNS
]

def is_private_ip(ip: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
        return any(ip_obj in network for network in PRIVATE_IP_RANGES)
    except ValueError:
        return False

def is_reserved_ip(ip: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
        return any(ip_obj in network for network in PRIVATE_IP_RANGES) or ip in DNS_SERVER_IPS
    except ValueError:
        return False

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    keyboard = [[InlineKeyboardButton("Add Domain", callback_data='adddomain')],
                [InlineKeyboardButton("Clear Domain", callback_data='cleardomain')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(rf"Hi {user.mention_html()}! Available commands:", reply_markup=reply_markup)

async def ask_ip(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Please enter the IP address for the new subdomain:")
    return ASK_IP

async def adddomain(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_id = user.id
    ip_address = update.message.text

    if is_private_ip(ip_address):
        await update.message.reply_text("Private IP addresses are not allowed.")
        return ConversationHandler.END

    if is_reserved_ip(ip_address):
        await update.message.reply_text("Reserved IP addresses are not allowed.")
        return ConversationHandler.END

    if user_id not in user_subdomains:
        user_subdomains[user_id] = []
    if len(user_subdomains[user_id]) < 5:
        selected_domain = random.choice(available_domains)
        new_subdomain = generate_random_subdomain(selected_domain)

        if any(reserved in new_subdomain for reserved in RESERVED_DOMAINS):
            await update.message.reply_text("The generated subdomain is reserved. Please try again.")
            return ConversationHandler.END

        user_subdomains[user_id].append({'subdomain': new_subdomain, 'ip': ip_address})
        cloudflare_info = cloudflare_configs.get(selected_domain)
        if not cloudflare_info:
            await update.message.reply_text("Cloudflare information for the selected domain is not set. Please ask the admin to set it up.")
            return ConversationHandler.END
        create_subdomain(new_subdomain, ip_address, cloudflare_info['api_key'], cloudflare_info['zone_id'], cloudflare_info['email'])
        # Notify the user
        await update.message.reply_text(
            f"🔔 New Sub-Domain Created!\n\n"
            f"👤 Admin: @{ADMIN_USERNAME}\n\n"
            f"🌐 Subdomain: {new_subdomain}\n"
            f"📍 IP Address: {ip_address}"
        )
        # Notify the admin
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                f"🔔 New Sub-Domain Created!\n\n"
                f"👤 User: @{user.username if user.username else user.full_name}\n"
                f"🆔 User ID: {user_id}\n"
                f"🌐 Subdomain: {new_subdomain}\n"
                f"📍 IP Address: {ip_address}"
            )
        )
    else:
        await update.message.reply_text("You have reached the limit of 5 subdomains. Use /cleardomain to remove one.")
    return ConversationHandler.END

async def cleardomain(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    if user_id in user_subdomains and user_subdomains[user_id]:
        keyboard = [[InlineKeyboardButton(subdomain['subdomain'], callback_data=subdomain['subdomain'])] for subdomain in user_subdomains[user_id]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Please choose the subdomain to clear:', reply_markup=reply_markup)
    else:
        await query.edit_message_text("You have no subdomains to remove.")

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'adddomain':
        await ask_ip(update, context)
    elif data == 'cleardomain':
        await cleardomain(update, context)
    else:
        subdomain = data
        user_id = query.from_user.id
        if user_id in user_subdomains:
            subdomains = user_subdomains[user_id]
            subdomain_to_remove = next((s for s in subdomains if s['subdomain'] == subdomain), None)
            if subdomain_to_remove:
                user_subdomains[user_id].remove(subdomain_to_remove)
                await query.edit_message_text(text=f"Subdomain {subdomain} has been removed.")
            else:
                await query.edit_message_text(text="Subdomain removal failed. Please try again.")

async def admin_adddomain_start(update: Update, context: CallbackContext) -> int:
    if str(update.effective_user.id) != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to add domains.")
        return ConversationHandler.END
    await update.message.reply_text("Please provide the Cloudflare API key:")
    return ASK_API_KEY

async def ask_zone_id(update: Update, context: CallbackContext) -> int:
    context.user_data['api_key'] = update.message.text
    await update.message.reply_text("Please provide the Cloudflare Zone ID:")
    return ASK_ZONE_ID

async def ask_email(update: Update, context: CallbackContext) -> int:
    context.user_data['zone_id'] = update.message.text
    await update.message.reply_text("Please provide the Cloudflare email:")
    return ASK_EMAIL

async def ask_domain(update: Update, context: CallbackContext) -> int:
    context.user_data['email'] = update.message.text
    await update.message.reply_text("Please provide the domain to add:")
    return ASK_DOMAIN

async def finalize_add_domain(update: Update, context: CallbackContext) -> int:
    new_domain = update.message.text
    api_key = context.user_data['api_key']
    zone_id = context.user_data['zone_id']
    email = context.user_data['email']
    if any(reserved in new_domain for reserved in RESERVED_DOMAINS):
        await update.message.reply_text("The domain is reserved. Please try again.")
        return ConversationHandler.END
    cloudflare_configs[new_domain] = {'api_key': api_key, 'zone_id': zone_id, 'email': email}
    available_domains.append(new_domain)
    await update.message.reply_text(f"Domain {new_domain} has been added to the pool with the provided API key, zone ID, and email.")
    return ConversationHandler.END

async def list_domains(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to list domains.")
        return
    await update.message.reply_text("Available domains:\n" + "\n".join(available_domains))

async def list_all_subdomains(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to list all subdomains.")
        return
    if user_subdomains:
        all_subdomains = []
        for user_id, subdomains in user_subdomains.items():
            user = await context.bot.get_chat(user_id)
            username = '@' + (user.username if user.username else user.full_name)
            for sub in subdomains:
                all_subdomains.append(f"Username: {username}, Subdomain: {sub['subdomain']}, IP: {sub['ip']}")
        all_subdomains_text = '\n'.join(all_subdomains)
        await update.message.reply_text(f"All subdomains added by all users:\n{all_subdomains_text}")
    else:
        await update.message.reply_text("No subdomains have been added yet.")

def generate_random_subdomain(domain):
    random_text = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    return f"{random_text}.{domain}"

def create_subdomain(subdomain, ip_address, api_key, zone_id, email):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"type": "A", "name": subdomain, "content": ip_address, "ttl": 1, "proxied": False}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        logger.error(f"Failed to create subdomain: {response.text}")
        raise Exception(f"Failed to create subdomain: {response.text}")

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('admin_adddomain', admin_adddomain_start)],
        states={
            ASK_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_zone_id)],
            ASK_ZONE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_domain)],
            ASK_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalize_add_domain)],
        },
        fallbacks=[]
    )
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_ip, pattern='^adddomain$')],
        states={ASK_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, adddomain)]},
        fallbacks=[]
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(admin_conv_handler)
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("list_domains", list_domains))
    application.add_handler(CommandHandler("admin_allsub", list_all_subdomains))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()

if __name__ == '__main__':
    main()