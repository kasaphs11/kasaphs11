import json
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import Forbidden, BadRequest
from collections import OrderedDict
from telegram.constants import ParseMode



main_keyboard_betyz = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton("/start"), KeyboardButton("/join")],
              [KeyboardButton("/payment"), KeyboardButton("/info")]],
    resize_keyboard=True
)


class ChannelInviteHandler:
    def __init__(self, application, admin_id):
        self.application = application
        self.admin_id = admin_id  # Telegram user ID του admin
        self.bot = application.bot
        self.approved_queue = asyncio.Queue()
        self.pending_requests = set()
        self.warned_users = set()
        self.dm_blocked_users = set()
        


        self.user_data_files = {
            "betyz": "json/user_data_betyz.json",
        }
        self.addlist_links = {
            "betyz": [
                "https://t.me/addlist/a9O1RAtutkE5YzQ8"
            ]
        }
        

        
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("payment", self.handle_payment))
        application.add_handler(CommandHandler("info", self.handle_info))
        application.add_handler(CommandHandler("join", self.handle_join_request))
        application.add_handler(CallbackQueryHandler(self.handle_approval_response))

       





    def _sorted_user_data(self, data: dict) -> dict:
        """Επιστρέφει data ταξινομημένο με end_date (πιο κοντινές λήξεις πρώτες)."""
        def sort_key(item):
            _uid, rec = item
            try:
                return datetime.strptime(rec.get("end_date", ""), "%d/%m/%Y %H:%M:%S")
            except Exception:
                # βάλ’ τα ‘χαλασμένα’ στο τέλος
                return datetime.max
        # κρατάμε και τυχόν ειδικά κλειδιά στο τέλος (π.χ. total_members)
        special = {}
        if "total_members" in data:
            special["total_members"] = data.pop("total_members")
        ordered = OrderedDict(sorted(data.items(), key=sort_key))
        ordered.update(special)
        return ordered

    


    
    async def check_access(self, update, context):
        return True

    
    WELCOME_TEXT = (
            "Welcome to Betyz Resell 🤖.\n\n"
            "Use the buttons below to continue.\n\n"
            "/join — Request for participation\n"
            "/payment — How to pay (Paysafe, Revolut)\n"
            "/info — Subscription details\n"
        )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📬 Join", callback_data="run_join")],
            [InlineKeyboardButton("💳 Pay", callback_data="run_payment")],
            [InlineKeyboardButton("ℹ️ Info", callback_data="run_info")],
        ])

        contact_line = "📩 Contact: @Betyz11"

        text = f"{self.WELCOME_TEXT}\n{contact_line}\n"

        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )


    async def handle_join_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_access(update, context):
            return

        # Works for both: command (/join) and inline button
        source_msg = update.message or (update.callback_query.message if update.callback_query else None)
        if source_msg is None:
            return

        user = update.effective_user
        user_id = user.id
        plan = self.get_user_plan(user_id) or "betyz"

        data = self.load_user_data_for(plan)
        now = datetime.now()
        user_info = data.get(str(user_id))

        # Already subscribed → show renewal button instead
        if user_info:
            end_date = datetime.strptime(user_info["end_date"], "%d/%m/%Y %H:%M:%S")
            if end_date > now:
                renew_kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔁 Renewal (+30 days)", callback_data=f"renew:{plan}:{user_id}")
                ]])
                await source_msg.reply_text(
                    "✅ Your subscription is already active.\n"
                    "If you want to renew, tap the button below.",
                    reply_markup=renew_kb
                )
                return

        # Already pending request
        if user_id in self.pending_requests:
            await source_msg.reply_text(
                "⏳ You already have a pending join request.\n"
                "Please wait for the admin to review it."
            )
            return

        # Create approval keyboard for admin
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve ", callback_data=f"approve:{plan}:{user_id}"),
            InlineKeyboardButton("🧪 Trial 3d",   callback_data=f"trial:{plan}:{user_id}"),
            InlineKeyboardButton("❌ Reject",     callback_data=f"reject:{plan}:{user_id}"),
        ]])

        # Message to admin
        username = f"@{user.username}" if user.username else "—"
        admin_text = (
            f"📥 New join request\n"
            f"Name: {user.full_name}\n"
            f"Username: {username}\n"
            f"ID: <code>{user_id}</code>"
        )

        await context.bot.send_message(
            chat_id=self.admin_id,
            text=admin_text,
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
        )

        self.pending_requests.add(user_id)

        # Info to user
        await source_msg.reply_text(
            "📬 Your request has been sent. To be accepted, send a message to the administrator @Betyz11 ."
        )


    async def safe_dm(self, bot, uid: int, text: str, **kwargs) -> bool:
        # αν ξέρουμε ήδη ότι έχει μπλοκάρει, μην προσπαθείς ξανά
        if uid in self.dm_blocked_users:
            return False
        try:
            await bot.send_message(chat_id=uid, text=text, **kwargs)
            return True
        except (Forbidden, BadRequest):
            # μην τυπώνεις τίποτα, απλώς σημείωσέ τον για να μην τον ξαναενοχλείς
            self.dm_blocked_users.add(uid)
            return False
        except Exception:
            # άλλο σφάλμα → απλώς μην στείλεις
            return False
        
    async def safe_edit(self, query, text: str):
        try:
            await query.edit_message_text(text)
        except BadRequest as e:
            msg = (getattr(e, "message", "") or str(e)).lower()
            if ("message is not modified" in msg or
                "message to edit not found" in msg or
                "message can't be edited" in msg):
                return
            print(f"[safe_edit] BadRequest: {e}")
        except Forbidden:
            return
        except Exception as e:
            print(f"[safe_edit] Unexpected: {e}")


    async def handle_approval_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data
        if data == "run_join":
            return await self.handle_join_request(update, context)

        if data == "run_payment":
            return await self.handle_payment(update, context)

        if data == "run_info":
            return await self.handle_info(update, context)

        if data == "payment_paysafe":
            await query.message.reply_text(
                "💳 Βάλτε το ποσό και ΜΗΝ ΤΣΕΚΑΡΕΤΕ ΤΗΝ ΕΠΙΛΟΓΗ που έχω υπογραμμισμένη με κόκκινο χρώμα , όταν γίνει η πληρωμή θα σας εμφανίσει έναν 16ψηφιο τον οποιο θα τον στείλετε στον διαχειριστή. Αφού ολοκληρώσετε την πληρωμή, πατήστε /join."
            )
            await query.message.reply_photo(photo="paysafe.png")
            return

        if data == "payment_revolut":
            await query.message.reply_text(
                "🔵 Pay with Revolut at the link below:\n👉 https://revolut.me/stefanxhyz \n" 
                "After completing the payment, press /join and send a message to the administrator to update about your payment."
            )
            return
        
        parts = query.data.split(":")
        action = parts[0]

        if action in ("approve", "trial", "reject", "renew", "renew_approve", "renew_reject"):
            plan = parts[1]
            user_id = int(parts[2])
            user = await context.bot.get_chat(user_id)

        else:
            return



        if action == "approve":
            now = datetime.now()
            # γράφουμε τον χρήστη στο σωστό plan
            self.update_user_data(user_id, user.full_name, now, now + timedelta(days=30), plan)
            self.warned_users.discard(str(user_id))

            # ενημέρωσε τον admin άμεσα
            try:
                await self.safe_edit(query, f"✅ Έγκριση ,{user.full_name}({plan.upper()}): θα σταλούν τα links .")
            except Exception:
                pass

            # unban pipeline να τρέξει άμεσα (όπως πριν)
            await self.approved_queue.put(user_id)

            # ⏳ στείλε τα links μετά από 30''
            async def send_links_later():
                await asyncio.sleep(10) 

                kb = main_keyboard_betyz
                # 1) Μήνυμα έγκρισης + επικεφαλίδα
                await self.safe_dm(
                    context.bot,
                    user_id,
                    f"✅ Your subscription to {plan.upper()} VIP!\n\n🔗 Join links:",
                    reply_markup=kb
                )

                # 2) & 3) Κάθε link σε ξεχωριστό μήνυμα
                links = self.addlist_links.get(plan, [])
                if isinstance(links, list):
                    for url in links:
                        await self.safe_dm(context.bot, user_id, url)
                elif links:
                    # αν είναι απλό string (fallback)
                    await self.safe_dm(context.bot, user_id, links)


            asyncio.create_task(send_links_later())




        if action == "trial":
            now = datetime.now()
            # trial 3 ημερών
            self.update_user_data(user_id, user.full_name, now, now + timedelta(days=3), plan)
            self.warned_users.discard(str(user_id))

            # ενημέρωσε τον admin άμεσα
            try:
                await self.safe_edit(query, f"🧪 TRIAL {user.full_name},({plan.upper()}): θα σταλούν τα links.")

            except Exception:
                pass

            # unban pipeline να τρέξει άμεσα (όπως πριν)
            await self.approved_queue.put(user_id)

    
            # ⏳ στείλε τα links μετά από 30''
            async def send_links_later():
                await asyncio.sleep(30)  # ή 15 αν θες

                kb = main_keyboard_betyz
                # 1) Μήνυμα έγκρισης + επικεφαλίδα
                await self.safe_dm(
                    context.bot,
                    user_id,
                    f"🧪 Your 3-day trial for {plan.upper()} VIP!\n\n🔗 Join links:",
                    reply_markup=kb
                )

                # 2) & 3) Κάθε link σε ξεχωριστό μήνυμα
                links = self.addlist_links.get(plan, [])
                if isinstance(links, list):
                    for url in links:
                        await self.safe_dm(context.bot, user_id, url)
                elif links:
                    # αν είναι απλό string (fallback)
                    await self.safe_dm(context.bot, user_id, links)


            asyncio.create_task(send_links_later())

        
        if action == "reject":
            ok = await self.safe_dm(context.bot, user_id, "❌ Your request was rejected.")
            await self.safe_edit(query, f"⛔ Απόρριψη ({plan.upper()}) για τον {user.full_name}.")


        if action == "renew":
            # μήνυμα στον admin με approve / reject για ΑΝΑΝΕΩΣΗ
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve +30d", callback_data=f"renew_approve:{plan}:{user_id}"),
                InlineKeyboardButton("❌ Reject",        callback_data=f"renew_reject:{plan}:{user_id}")
            ]])
            await context.bot.send_message(
                chat_id=self.admin_id,
                text=f"🔁 Αίτημα ΑΝΑΝΕΩΣΗΣ από: @{user.username or user.first_name}\n🆔 ID: {user_id}\n📦 Plan: {plan.upper()}",
                reply_markup=kb
            )
            # ενημέρωσε το tap του admin (στο αρχικό μήνυμα)
            await self.safe_edit(query, "🔁 Renewal request sent to admin.")
            return

        if action == "renew_approve":
            data = self.load_user_data_for(plan)
            rec = data.get(str(user_id))

            now = datetime.now()
            if rec:
                # πάρε το τρέχον end_date και πρόσθεσε 30 μέρες από το ΜΕΓΙΣΤΟ(now, end)
                old_end = datetime.strptime(rec["end_date"], "%d/%m/%Y %H:%M:%S")
                base = old_end if old_end > now else now
                new_end = base + timedelta(days=30)
                rec["end_date"] = new_end.strftime("%d/%m/%Y %H:%M:%S")
                # (προαιρετικό) ΜΗν αλλάζεις start_date
                data[str(user_id)] = rec
                self.save_user_data_for(plan, data)

                # ενημέρωσε admin & χρήστη
                await self.safe_edit(query, f"✅ Renewal completed for +30 days ({plan.upper()}).")
                await self.safe_dm(
                    context.bot, user_id,
                    f"🔁 Your subscription has been renewed until {rec['end_date']}."
                )
            else:
                # δεν υπήρχε εγγραφή—προαιρετικά: ξεκίνα νέα 30ήμερη
                new_end = now + timedelta(days=30)
                self.update_user_data(user_id, user.full_name, now, new_end, plan)
                await self.safe_edit(query, f"ℹ️ Δεν υπήρχε ενεργή εγγραφή — δημιουργήθηκε νέα 30ήμερη ({plan.upper()}).")
                await self.safe_dm(
                    context.bot, user_id,
                    f"🔁 Ενεργοποιήθηκε νέα 30ήμερη μέχρι {new_end.strftime('%d/%m/%Y %H:%M:%S')}."
                )
            return

        if action == "renew_reject":
            await self.safe_edit(query, "⛔ Απόρριψη ανανέωσης.")
            # δεν στέλνουμε τίποτα στον χρήστη (όπως ζήτησες)
            return

        
    

        if "unban_queue" not in self.application.bot_data:
            self.application.bot_data["unban_queue"] = asyncio.Queue()

        self.pending_requests.discard(user_id)
    
    async def wait_for_approval(self):
        return await self.approved_queue.get()

    async def handle_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_access(update, context):
            return

        # Works for both: /payment and inline "Pay" button
        source_msg = update.message or (update.callback_query.message if update.callback_query else None)
        if source_msg is None:
            return

        payment_text = (
            "💵 Subscription: €10 / 30 days\n\n"
            "Available payment methods:\n"
            "• Paysafe\n"
            "• Revolut\n\n"
            "After payment, send your receipt or screenshot here so the admin can verify it."
        )

        await source_msg.reply_text(payment_text)

        keyboard = [
            [
                InlineKeyboardButton("🔴 Paysafe", callback_data="payment_paysafe"),
                InlineKeyboardButton("🔵 Revolut", callback_data="payment_revolut"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await source_msg.reply_text(
            "💳 Choose a payment method:",
            reply_markup=reply_markup
        )




    async def handle_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_access(update, context):
            return

        # Works for both: /info and inline "Info" button
        source_msg = update.message or (update.callback_query.message if update.callback_query else None)
        if source_msg is None:
            return

        user = update.effective_user
        user_id = user.id
        plan = self.get_user_plan(user_id) or "betyz"

        data = self.load_user_data_for(plan)
        info = data.get(str(user_id))

        now = datetime.now()
        status = "Not subscribed 🔴"
        start_str = "—"
        end_str = "—"

        if info:
            start_dt = datetime.strptime(info["start_date"], "%d/%m/%Y %H:%M:%S")
            end_dt = datetime.strptime(info["end_date"], "%d/%m/%Y %H:%M:%S")
            start_str = start_dt.strftime("%d/%m/%Y %H:%M:%S")
            end_str = end_dt.strftime("%d/%m/%Y %H:%M:%S")
            if end_dt > now:
                status = "Subscribed 🟢"

        username = f"@{user.username}" if user.username else f"ID: {user_id}"

        text = (
            f"✨ User Details ✨\n"
            f"👤 {username}\n"
            f"Subscription Details:\n"
            f"🚦Status: {status}\n"
            f"⏳Start: {start_str}\n"
            f"📅End: {end_str}"
        )

        await source_msg.reply_text(text)


        
    def get_user_plan(self, user_id: int) -> str | None:
        return "betyz"


    def load_user_data_for(self, plan: str):
        path = self.user_data_files[plan]
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_user_data_for(self, plan: str, data: dict):
        path = self.user_data_files[plan]
        data = self._sorted_user_data(dict(data))  # ⬅️ ταξινόμηση πριν το dump
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    
    #json
    def update_user_data(self, user_id, full_name, start_date, end_date, plan: str):
        data = self.load_user_data_for(plan)
        data[str(user_id)] = {
            "user_id": user_id,
            "full_name": full_name or "N/A",
            "start_date": start_date.strftime("%d/%m/%Y %H:%M:%S"),
            "end_date": end_date.strftime("%d/%m/%Y %H:%M:%S")
        }
        self.save_user_data_for(plan, data)


    async def remove_expired_users(self):
        now = datetime.now()
        warning_seconds = 86400

        for plan in ("betyz",):
            data = self.load_user_data_for(plan)
            to_remove = []

            for user_id, rec in list(data.items()):
                if user_id == "total_members": 
                    continue
                end_str = rec.get("end_date")
                if not end_str:
                    continue
                end_dt = datetime.strptime(end_str, "%d/%m/%Y %H:%M:%S")
                time_to_end = (end_dt - now).total_seconds()

                if 0 < time_to_end <= warning_seconds and user_id not in self.warned_users:
                    try:
                        ok = await self.safe_dm(
                            self.bot,
                            int(user_id),
                            "⚠️ Your subscription expires tomorrow! If you want to renew, please contact the administrator."
                        )
                        if ok:
                            self.warned_users.add(user_id)
                    except:
                        pass

                if now > end_dt:
                    to_remove.append(user_id)
                    self.warned_users.discard(user_id)

            for uid in to_remove:
                del data[uid]
            if to_remove:
                self.save_user_data_for(plan, data)
                
                
