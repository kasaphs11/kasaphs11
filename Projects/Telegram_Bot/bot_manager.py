import time
import threading
import asyncio
import json

from blade_bot import BladeBot
from channel_invite_bot import ChannelInviteHandler
from access_control import AccessControl

from telegram.ext import Application, CommandHandler, filters


# ---------------------------------------------------------
# 1) ΠΡΟΑΙΡΕΤΙΚΟ: πάρε Telethon client από "αλλού"
#    Αν έχεις ήδη module που φτιάχνει/κρατάει client, βάλε το εδώ.
#
#    Παράδειγμα:
#       from my_telethon_client import telethon_client as EXTERNAL_TELETHON_CLIENT
#
#    Αν ΔΕΝ υπάρχει, άφησέ το None και θα γίνει fallback.
# ---------------------------------------------------------
EXTERNAL_TELETHON_CLIENT = None

try:
    # άλλαξέ το σε αυτό που έχεις πραγματικά
    # from telethon_client_holder import client as EXTERNAL_TELETHON_CLIENT
    pass
except Exception:
    EXTERNAL_TELETHON_CLIENT = None


class BotManager:
    def __init__(self):
        self.telegram_token = ""

        self.chat_id_1 = 
        self.chat_id_2 = 
        self.admin = 
        self.chat_id_disconnected = 

        with open("json/group_ids_betyz.json", "r", encoding="utf-8") as f:
            self.group_ids_betyz = json.load(f)["group_ids"]

        # --- PTB Application ---
        self.application = Application.builder().token(self.telegram_token).post_init(self.post_init).build()

        self.application.add_handler(CommandHandler("getid", self.cmd_getid))  # groups/PM
        self.application.add_handler(
            CommandHandler("getid", self.cmd_getid_channel, filters=filters.ChatType.CHANNEL)
        )  # channels

        # --- Blade bot ---
        self.blade_bot = BladeBot(
            driver_path=r"C:\chromedriver-win64\chromedriver.exe",
            telegram_token=self.telegram_token,
            chat_id_1=self.chat_id_1,
            chat_id_2=self.chat_id_2,
            chat_id_disconnected=self.chat_id_disconnected,
        )

        # --- Channel invite ---
        self.channel_invite_handler = ChannelInviteHandler(
            application=self.application,
            admin_id=self.admin,
        )

        # --- Telethon client (είτε external είτε fallback) ---
        self.telethon_client = EXTERNAL_TELETHON_CLIENT

        # AccessControl θα αρχικοποιηθεί στο post_init (για να έχουμε event loop)
        self.access_betyz = None

    # ------------------ Telegram helpers ------------------
    async def cmd_getid(self, update, context):
        chat = update.effective_chat
        kind = getattr(chat, "type", "unknown")
        await update.message.reply_text(f"Chat ID: {chat.id}\nType: {kind}")

    async def cmd_getid_channel(self, update, context):
        chat = update.effective_chat
        msg = update.effective_message
        text = f"Channel ID: {chat.id}\nType: {getattr(chat, 'type', 'channel')}"
        if msg:
            await msg.reply_text(text)
        else:
            await context.bot.send_message(chat_id=chat.id, text=text)

    # ------------------ Blade loop ------------------
    def run_blade_bot(self):
        while True:
            self.blade_bot.check_and_send_tickets()
            time.sleep(0.5)

    # ------------------ PTB post_init ------------------
    async def post_init(self, app):
        """
        Τρέχει μέσα στο asyncio loop του python-telegram-bot.
        Εδώ ξεκινάμε AccessControl tasks και expiration/approvals.
        """
        # Αν ΔΕΝ υπάρχει external telethon client, κάνε fallback δημιουργία εδώ.
        if self.telethon_client is None:
            from telethon import TelegramClient

            # 🔧 Βάλε εδώ τα δικά σου (ή κάν’ τα env vars)
            api_id = 29990481
            api_hash = "c8084f89e07ea776850faea8a14e07e9"
            session_name = "my_session"  # ή το session που ήδη χρησιμοποιείς

            self.telethon_client = TelegramClient(session_name, api_id, api_hash)
            await self.telethon_client.start()
        else:
            # Αν είναι external, απλά βεβαιώσου ότι είναι συνδεδεμένο.
            try:
                if hasattr(self.telethon_client, "is_connected") and not self.telethon_client.is_connected():
                    # αν ο external client θέλει start/connect
                    if hasattr(self.telethon_client, "start"):
                        await self.telethon_client.start()
            except Exception:
                # αν ο external client το χειρίζεται αλλιώς, μην σπάσουμε το boot
                pass

        # --- AccessControl ---
        self.access_betyz = AccessControl(
            client=self.telethon_client,
            group_ids=self.group_ids_betyz,
            user_data_file="json/user_data_betyz.json",
            scan_interval_sec=15,
            per_action_sleep=0.15,
            concurrency=6,
        )

        # tasks
        asyncio.create_task(self.access_betyz.start_periodic_scan())
        asyncio.create_task(self.run_expiration_checker())
        asyncio.create_task(self.handle_approvals())

    # ------------------ Approvals pipeline ------------------
    async def handle_approvals(self):
        while True:
            user_id = await self.channel_invite_handler.wait_for_approval()
            print(f"✅ Νέος approved χρήστης: {user_id} → UNBAN σε όλα τα groups")

            try:
                if self.access_betyz is not None:
                    await self.access_betyz.unban_all_now(user_id)
            except Exception as e:
                print(f"⚠️ UNBAN error for {user_id}: {e}")

            await asyncio.sleep(1)

    # ------------------ Expiration checker ------------------
    async def run_expiration_checker(self):
        while True:
            try:
                await self.channel_invite_handler.remove_expired_users()
            except Exception as e:
                print(f"⚠️ remove_expired_users error: {e}")
            await asyncio.sleep(1)

    # ------------------ Runner ------------------
    def run(self):
        threading.Thread(target=self.run_blade_bot, daemon=True).start()
        self.application.run_polling()


if __name__ == "__main__":
    manager = BotManager()
    manager.run()
