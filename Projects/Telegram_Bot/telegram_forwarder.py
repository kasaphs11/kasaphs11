from telethon import TelegramClient, events
import asyncio
import os
import re
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import cv2
import numpy as np
import time, uuid

# Διαδρομή στο Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class TelegramForwarder:
    def __init__(self, api_id, api_hash, chat_pairs):
        """
        chat_pairs: List of (source_chat_id, target_chat_id) tuples
        """
        self.chat_pairs = chat_pairs
        os.makedirs("sessions", exist_ok=True)
        session_path = r"sessions/forwarder_session"
        self.client = TelegramClient(session_path, api_id, api_hash)

        self.handlers = {}  # {src_id: <handler func>}

        # Κανονικές εκφράσεις για links, mentions, wins
        self.LINK_REGEX = r"(t\.me/)"
        self.MENTION_REGEX = r"@\w+"
        self.WINS_REGEX = r"wins.*✅{3,}"

                # Φράσεις/μοτίβα που μπλοκάρουμε
        self.blocked_phrases = [
            "original resell:",
            "perumal_resell",
            "the button",
            "free access",           # π.χ. "Free access"
            "pre pinnacle drop",     # π.χ. "Pre Pinnacle Drop"
            "write to me",           # π.χ. "Write to me so that I can add you"
            "write me",
            "dm me"
        ]

        # Regex για πιο γενικά patterns (π.χ. +VINLIEtOjw4NWVi)
        self.blocked_regexes = [
            r"\bperumal\b",
            r"\bfree\s*access\b",
            r"\bpre\s*pinnacle\s*drop\b",
            r"\bwrite\s+to\s+me\b",
            r"\bwrite\s+me\b",
            r"\bdm\s+me\b",
            r"\+[A-Za-z0-9]{6,}"     # “promo/πρόσκληση” κώδικες τύπου +VINL...
        ]


    def clean_text(self, message_text):
        """Αφαιρεί links και mentions από κείμενο"""
        text = re.sub(self.LINK_REGEX, '', message_text)
        text = re.sub(self.MENTION_REGEX, '', text)
        return text.strip()
    
    def should_block_message(self, text):
        lt = text.lower()
        if any(p in lt for p in self.blocked_phrases):
            return True
        for rx in self.blocked_regexes:
            if re.search(rx, lt):
                return True
        return False



    def check_for_original_resell(self, file_path):
        """Ελέγχει μέσω OCR αν υπάρχει 'Original' και 'Resell' στο image, για να μπλοκάρει"""
        try:
            img = cv2.imread(file_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
            data = pytesseract.image_to_string(thresh).lower()
            return 'original' in data and 'resell' in data
        except Exception as e:
            print(f"❌ Σφάλμα στο check_for_original_resell: {e}")
            return False

    async def make_forward_handler(self, target_chat_id):
        async def handler(event):
            try:
                raw_text = event.message.message or ''

                # 1) μπλοκάρουμε links/mentions/wins ΣΤΟ ΑΡΧΙΚΟ κείμενο
                if re.search(self.LINK_REGEX, raw_text) or \
                re.search(self.MENTION_REGEX, raw_text) or \
                re.search(self.WINS_REGEX, raw_text):
                    return

                # μετά κάνουμε cleaning για να στείλουμε "καθαρό" κείμενο
                clean_msg = self.clean_text(raw_text)

                # 2) blocklists/regex πάνω στο καθαρό κείμενο
                if self.should_block_message(clean_msg):
                    return

                if event.message.media:
                    # επιτρέπουμε μόνο κανονικές εικόνες
                    mime = getattr(event.message, "file", None)
                    mime = getattr(mime, "mime_type", "") if mime else ""
                    is_image = mime.startswith("image/") and not mime.endswith("/webp")

                    if not is_image:
                        # αν δεν είναι εικόνα, απλά στείλ’ το χωρίς OCR ή παράβλεψέ το
                        # π.χ. forward/ send_file απευθείας ή return
                        # return
                        path = await event.message.download_media()
                        if not path:
                            print("❌ download_media επέστρεψε None (μη εικόνα).")
                            return
                        await self.client.send_file(target_chat_id, path, caption=clean_msg)
                        return

                    # για εικόνα -> κατέβασε σε μοναδικό προσωρινό path
                    os.makedirs("temp_media", exist_ok=True)
                    temp_path = os.path.join(
                        "temp_media",
                        f"{event.message.id}_{int(time.time())}_{uuid.uuid4().hex}.jpg"
                    )
                    try:
                        path = await event.message.download_media(file=temp_path)
                        if not path or not os.path.exists(path):
                            print(f"❌ Αποτυχία download_media: {path}")
                            return

                        # διάβασε την εικόνα με OpenCV
                        img = cv2.imread(path)
                        if img is None:
                            print(f"❌ cv2.imread γύρισε None για {path}")
                            return

                        # εδώ κάνε το cvtColor/ocr σου με ασφάλεια
                        # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # μόνο αν χρειάζεται

                        # έλεγχος για resell (OCR)
                        if self.check_for_original_resell(path):
                            return

                        await self.client.send_file(target_chat_id, path, caption=clean_msg)

                    finally:
                        try:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        except:
                            pass


                elif event.message.text:
                    await self.client.send_message(target_chat_id, clean_msg)

            except Exception as e:
                print(f"❌ Σφάλμα στο forwarding: {e}")
        return handler

    def _normalize_pairs(self, pairs):
        """επιστρέφει set από tuples (src, to) από dicts ή tuples."""
        wanted = set()
        for p in pairs or []:
            if isinstance(p, dict):
                src = int(p["from"]); to = int(p["to"])
            else:
                src = int(p[0]); to = int(p[1])
            wanted.add((src, to))
        return wanted

    async def _bind_pair(self, src, to):
        """φτιάχνει handler για ΖΕΥΓΑΡΙ με την ΥΠΑΡΧΟΥΣΑ make_forward_handler."""
        h = await self.make_forward_handler(to)
        self.client.add_event_handler(h, events.NewMessage(chats=src))
        self.handlers[(src, to)] = h

    def set_chat_pairs(self, pairs):
        """
        Εφαρμόζει δυναμικά νέα ζευγάρια ΧΩΡΙΣ restart,
        χρησιμοποιώντας την ήδη υπάρχουσα make_forward_handler.
        """
        wanted = self._normalize_pairs(pairs)
        current = set(self.handlers.keys())

        # 1) Αφαίρεσε handlers που δεν χρειάζονται πλέον
        for key in current - wanted:
            h = self.handlers.pop(key, None)
            if h:
                try:
                    self.client.remove_event_handler(h)
                except Exception:
                    pass

        # 2) Πρόσθεσε handlers για νέα ζευγάρια
        for (src, to) in wanted - current:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._bind_pair(src, to))
            else:
                asyncio.run(self._bind_pair(src, to))


    async def main(self):
        await self.client.start()
        if self.chat_pairs:
            self.set_chat_pairs(self.chat_pairs)


    async def run_forever(self):
        await self.client.run_until_disconnected()

    def start(self):
        asyncio.run(self.main())