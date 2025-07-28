import os
import logging
import time
import secrets
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.error import BadRequest

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# MongoDB setup
MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = "telegram_forwarder"
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_col = db["users"]
channels_col = db["channels"]
force_sub_col = db["force_sub"]

# Environment variables
OWNER_ID = int(os.environ.get("OWNER_ID"))
SHORTENER_API_KEY = os.environ.get("SHORTENER_API_KEY", "")
SHORTENER_API_URL = os.environ.get("SHORTENER_API_URL", "")
VERIFICATION_INTERVAL = int(os.environ.get("VERIFICATION_INTERVAL", 24))  # in hours

# Bot commands setup
COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("setchannel", "Set target channel"),
    BotCommand("premium", "Premium features"),
    BotCommand("batchsave", "Save multiple media"),
    BotCommand("cancel", "Cancel current operation"),
    BotCommand("logout", "Logout from service"),
    BotCommand("resetall", "Reset all data (Owner only)"),
    BotCommand("broadcast", "Broadcast message (Owner only)"),
    BotCommand("addfchannel", "Add force-sub channel (Owner only)"),
    BotCommand("addfgroup", "Add force-sub group (Owner only)"),
    BotCommand("removefchannel", "Remove force-sub channel (Owner only)"),
    BotCommand("removefgroup", "Remove force-sub group (Owner only)"),
    BotCommand("setverifyinterval", "Set verification interval (Owner only)"),
    BotCommand("setshortener", "Set shortener API (Owner only)"),
]

# Force subscription status
FORCE_SUB_CHANNELS = []
FORCE_SUB_GROUPS = []

async def load_force_sub_data():
    global FORCE_SUB_CHANNELS, FORCE_SUB_GROUPS
    force_sub_data = force_sub_col.find_one({"_id": "force_sub_data"})
    if force_sub_data:
        FORCE_SUB_CHANNELS = force_sub_data.get("channels", [])
        FORCE_SUB_GROUPS = force_sub_data.get("groups", [])
    else:
        force_sub_col.insert_one({
            "_id": "force_sub_data",
            "channels": [],
            "groups": []
        })

async def generate_short_url(long_url: str) -> str:
    """Generate short URL using the shortener API"""
    if not SHORTENER_API_URL or not SHORTENER_API_KEY:
        logger.warning("Shortener API not configured")
        return long_url
    
    try:
        params = {
            "api": SHORTENER_API_KEY,
            "url": long_url,
            "format": "text"  # Get plain text response
        }
        
        response = requests.get(SHORTENER_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        return response.text.strip()
    except Exception as e:
        logger.error(f"Shortener API error: {e}")
        return long_url

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = users_col.find_one({"_id": user_id})
    
    if not user_data:
        users_col.insert_one({
            "_id": user_id,
            "username": update.effective_user.username,
            "channel": None,
            "premium": False,
            "last_verified": None
        })
    
    # Check force subscription
    if not await check_force_sub(update, context, user_id):
        return
    
    welcome_msg = (
        "🔓 *Save Restricted Content Bot*\n"
        "I can bypass forwarding restrictions!\n\n"
        "📌 *Features:*\n"
        "- Forward restricted content to channels\n"
        "- Get content in your personal messages\n"
        "- Batch save multiple media\n\n"
        "⚙️ *Setup Instructions:*\n"
        "1. Use /setchannel to configure target\n"
        "2. Forward restricted content to me\n\n"
        "💎 Use /premium for exclusive features"
    )
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode="MarkdownV2"
    )

async def check_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
        
    if not FORCE_SUB_CHANNELS and not FORCE_SUB_GROUPS:
        return True
        
    missing_channels = []
    missing_groups = []
    
    # Check channel subscriptions
    for channel in FORCE_SUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                missing_channels.append(channel)
        except Exception as e:
            logger.error(f"Force sub check error: {e}")
            missing_channels.append(channel)
    
    # Check group subscriptions
    for group in FORCE_SUB_GROUPS:
        try:
            member = await context.bot.get_chat_member(chat_id=group, user_id=user_id)
            if member.status in ['left', 'kicked']:
                missing_groups.append(group)
        except Exception as e:
            logger.error(f"Force sub check error: {e}")
            missing_groups.append(group)
    
    if not missing_channels and not missing_groups:
        return True
    
    # Create join buttons
    buttons = []
    for channel in missing_channels:
        try:
            chat = await context.bot.get_chat(channel)
            buttons.append([InlineKeyboardButton(f"Join {chat.title}", url=f"https://t.me/{chat.username}")])
        except:
            buttons.append([InlineKeyboardButton(f"Join Channel", url=f"https://t.me/{channel}")])
    
    for group in missing_groups:
        try:
            chat = await context.bot.get_chat(group)
            buttons.append([InlineKeyboardButton(f"Join {chat.title}", url=f"https://t.me/{chat.username}")])
        except:
            buttons.append([InlineKeyboardButton(f"Join Group", url=f"https://t.me/{group}")])
    
    buttons.append([InlineKeyboardButton("✅ I've Joined", callback_data="force_sub_verify")])
    
    await update.message.reply_text(
        "📢 To use Save Restricted Content Bot, please join our channels and groups:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return False

async def force_sub_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if await check_force_sub(query, context, user_id):
        await query.edit_message_text("✅ Thanks for joining! You can now use the bot.")
        await start(query, context)
    else:
        await query.answer("Please join all required channels and groups first!", show_alert=True)

async def check_verification(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
        
    user_data = users_col.find_one({"_id": user_id})
    if not user_data:
        return False
    
    # Premium users don't need verification
    if user_data.get("premium", False):
        return True
    
    # Check verification status
    last_verified = user_data.get("last_verified")
    if not last_verified:
        return False
    
    # Check if verification has expired
    verification_expiry = last_verified + timedelta(hours=VERIFICATION_INTERVAL)
    return datetime.utcnow() < verification_expiry

async def require_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_verification(user_id):
        return True
    
    # Generate unique verification token
    token = secrets.token_urlsafe(16)
    users_col.update_one(
        {"_id": user_id},
        {"$set": {"verify_token": token}}
    )
    
    # Create verification URL
    verification_url = f"https://t.me/{context.bot.username}?start=verify_{token}"
    
    # Generate short URL using API
    short_url = await generate_short_url(verification_url)
    
    await update.message.reply_text(
        "⏳ Your session has expired. Please verify to continue using Save Restricted Content Bot:\n\n"
        f"🔗 [Click here to verify]({short_url})",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔓 Verify Now", url=short_url)]
        ])
    )
    return False

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text("Please provide a verification token")
        return
    
    token = args[0]
    user_data = users_col.find_one({"_id": user_id})
    
    if user_data and user_data.get("verify_token") == token:
        users_col.update_one(
            {"_id": user_id},
            {"$set": {"last_verified": datetime.utcnow()}, "$unset": {"verify_token": ""}}
        )
        await update.message.reply_text("✅ Verification successful! You can now use the bot.")
    else:
        await update.message.reply_text("❌ Invalid verification token")

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check force subscription
    if not await check_force_sub(update, context, update.effective_user.id):
        return
    
    # Check verification for non-owner
    if update.effective_user.id != OWNER_ID and not await check_verification(update.effective_user.id):
        await require_verification(update, context)
        return
    
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text("Please specify a channel: /setchannel @channelname")
        return
    
    channel_username = args[0].lstrip('@')
    users_col.update_one(
        {"_id": user_id},
        {"$set": {"channel": channel_username}}
    )
    
    await update.message.reply_text(f"✅ Channel set: @{channel_username}\nNow send restricted content!")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check force subscription
    if not await check_force_sub(update, context, update.effective_user.id):
        return
    
    # Check verification for non-owner
    if update.effective_user.id != OWNER_ID and not await check_verification(update.effective_user.id):
        await require_verification(update, context)
        return
    
    user_id = update.effective_user.id
    user_data = users_col.find_one({"_id": user_id})
    
    if not user_data or not user_data.get("channel"):
        await update.message.reply_text("❌ Please set a channel first using /setchannel")
        return
    
    target_channel = f"@{user_data['channel']}"
    keyboard = [
        [InlineKeyboardButton("📩 Send to me", callback_data="send_to_me")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Forward media to target channel
        await context.bot.forward_message(
            chat_id=target_channel,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        
        # Confirmation message with button
        await update.message.reply_text(
            f"✅ Media forwarded successfully to {target_channel}\nWant it in your DM?",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Forwarding error: {e}")
        await update.message.reply_text("❌ Failed to forward media. Make sure I'm admin in target channel!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "send_to_me":
        try:
            # Forward to user privately
            await context.bot.forward_message(
                chat_id=query.from_user.id,
                from_chat_id=query.message.chat_id,
                message_id=query.message.reply_to_message.message_id
            )
            await query.edit_message_text("✅ Sent to your personal messages!")
        except Exception as e:
            logger.error(f"Personal forward error: {e}")
            await query.edit_message_text("❌ Failed to send. Please start a DM with me first!")
    
    elif query.data == "force_sub_verify":
        await force_sub_verify(update, context)

# Owner commands
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Owner only command!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    users = users_col.find()
    count = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user["_id"],
                text=f"📢 Broadcast from Save Restricted Content Bot:\n\n{message}"
            )
            count += 1
        except Exception as e:
            logger.error(f"Broadcast error to {user['_id']}: {e}")
    
    await update.message.reply_text(f"✅ Broadcast sent to {count} users")

async def resetall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Owner only command!")
        return
    
    users_col.delete_many({})
    channels_col.delete_many({})
    await update.message.reply_text("✅ All data has been reset")

async def add_fchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Owner only command!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /addfchannel @channel_username")
        return
    
    channel = args[0].lstrip('@')
    if channel not in FORCE_SUB_CHANNELS:
        FORCE_SUB_CHANNELS.append(channel)
        force_sub_col.update_one(
            {"_id": "force_sub_data"},
            {"$set": {"channels": FORCE_SUB_CHANNELS}}
        )
        await update.message.reply_text(f"✅ Force-sub channel added: @{channel}")
    else:
        await update.message.reply_text("⚠️ Channel already in force-sub list")

async def add_fgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Owner only command!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /addfgroup @group_username")
        return
    
    group = args[0].lstrip('@')
    if group not in FORCE_SUB_GROUPS:
        FORCE_SUB_GROUPS.append(group)
        force_sub_col.update_one(
            {"_id": "force_sub_data"},
            {"$set": {"groups": FORCE_SUB_GROUPS}}
        )
        await update.message.reply_text(f"✅ Force-sub group added: @{group}")
    else:
        await update.message.reply_text("⚠️ Group already in force-sub list")

async def remove_fchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Owner only command!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /removefchannel @channel_username")
        return
    
    channel = args[0].lstrip('@')
    if channel in FORCE_SUB_CHANNELS:
        FORCE_SUB_CHANNELS.remove(channel)
        force_sub_col.update_one(
            {"_id": "force_sub_data"},
            {"$set": {"channels": FORCE_SUB_CHANNELS}}
        )
        await update.message.reply_text(f"✅ Force-sub channel removed: @{channel}")
    else:
        await update.message.reply_text("⚠️ Channel not in force-sub list")

async def remove_fgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Owner only command!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /removefgroup @group_username")
        return
    
    group = args[0].lstrip('@')
    if group in FORCE_SUB_GROUPS:
        FORCE_SUB_GROUPS.remove(group)
        force_sub_col.update_one(
            {"_id": "force_sub_data"},
            {"$set": {"groups": FORCE_SUB_GROUPS}}
        )
        await update.message.reply_text(f"✅ Force-sub group removed: @{group}")
    else:
        await update.message.reply_text("⚠️ Group not in force-sub list")

async def set_verify_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Owner only command!")
        return
    
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /setverifyinterval <hours>")
        return
    
    global VERIFICATION_INTERVAL
    VERIFICATION_INTERVAL = int(args[0])
    os.environ["VERIFICATION_INTERVAL"] = str(VERIFICATION_INTERVAL)
    await update.message.reply_text(f"✅ Verification interval set to {VERIFICATION_INTERVAL} hours")

async def set_shortener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Owner only command!")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /setshortener <api_url> <api_key>")
        return
    
    global SHORTENER_API_URL, SHORTENER_API_KEY
    SHORTENER_API_URL = args[0]
    SHORTENER_API_KEY = args[1]
    
    # Test the API
    test_url = "https://google.com"
    try:
        short_url = await generate_short_url(test_url)
        await update.message.reply_text(
            f"✅ Shortener API configured successfully!\n"
            f"Test URL: {test_url}\n"
            f"Short URL: {short_url}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error testing shortener API: {e}")

# Additional commands
async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check force subscription
    if not await check_force_sub(update, context, update.effective_user.id):
        return
    
    await update.message.reply_text(
        "🌟 *Save Restricted Content Bot Premium Features*\n\n"
        "💎 *Ad-Free Experience*\n"
        "🚫 No verification required\n"
        "⚡ Priority processing\n"
        "📦 Increased batch save limits\n\n"
        "Contact @owner_username for premium access!",
        parse_mode="Markdown"
    )

async def batchsave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check force subscription
    if not await check_force_sub(update, context, update.effective_user.id):
        return
    
    # Check verification for non-owner
    if update.effective_user.id != OWNER_ID and not await check_verification(update.effective_user.id):
        await require_verification(update, context)
        return
    
    await update.message.reply_text("📦 Batch save activated. Send multiple media to Save Restricted Content Bot now...")

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_col.delete_one({"_id": update.effective_user.id})
    await update.message.reply_text("✅ You've been logged out from Save Restricted Content Bot")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Current operation canceled in Save Restricted Content Bot")

def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    
    # Create Application
    application = Application.builder().token(TOKEN).build()
    
    # Load force sub data
    application.create_task(load_force_sub_data())
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setchannel", set_channel))
    application.add_handler(CommandHandler("premium", premium))
    application.add_handler(CommandHandler("batchsave", batchsave))
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(CommandHandler("resetall", resetall))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("verify", verify_user))
    application.add_handler(CommandHandler("addfchannel", add_fchannel))
    application.add_handler(CommandHandler("addfgroup", add_fgroup))
    application.add_handler(CommandHandler("removefchannel", remove_fchannel))
    application.add_handler(CommandHandler("removefgroup", remove_fgroup))
    application.add_handler(CommandHandler("setverifyinterval", set_verify_interval))
    application.add_handler(CommandHandler("setshortener", set_shortener))
    
    # Media handler (photos, videos, documents)
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.Document.ALL,
        handle_media
    ))
    
    # Button handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Set bot commands
    application.bot.set_my_commands(COMMANDS)
    
    # Start bot
    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
    
    if WEBHOOK_URL:
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
            url_path=TOKEN
        )
    else:
        application.run_polling()

if __name__ == "__main__":
    main()
