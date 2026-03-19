# blade_bot.py
#chrome://settings/content/javascript

import os
import json
import time
import traceback
import requests
import sys
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
from selenium.webdriver.support.ui import WebDriverWait
from urllib.parse import urljoin



class BladeBot:
    def __init__(self, driver_path, telegram_token, chat_id_1, chat_id_2, chat_id_disconnected, cookies_file="json/cookies.json"):
        self.url = "https://www.blade.bet/myaccount/openbets"
        self.driver_path = driver_path
        self.telegram_token = telegram_token
        self.chat_id_1 = chat_id_1
        self.chat_id_2 = chat_id_2
        self.chat_id_disconnected = chat_id_disconnected
        self.cookies_file = cookies_file
        self.sent_ids_file = "json/sent_ids.txt"
        self.driver = self._init_driver()
        self.cookies = self.load_cookies()
        self.was_logged_out = False

        self.emoji_sources = {
            # format: src: (emoji, chat_id)
            "/docs/Images/BetCat/a54a45ab-cb8b-45be-bcb1-8c132b8dc31a.png": ("⚔️", chat_id_2),
            "/docs/Images/BetCat/e23d5d52-c9f5-41ff-b620-ba5ac8a30695.png": ("🪐", chat_id_2),
            "/docs/Images/BetCat/fc906c04-d481-45af-b4f5-84708412d66e.png": ("🏀", chat_id_2),
            "/docs/Images/BetCat/7199f06d-d2b4-4861-b941-122f5fd4661b.png": ("🐊", chat_id_2),
            "/docs/Images/BetCat/adb853e4-2e58-4f4a-942b-0982975b51dc.png": ("💰", chat_id_2),

            "/docs/Images/BetCat/0c04e335-1976-403e-9668-6acade298855.png": ("🚂", chat_id_2),

            "/docs/Images/BetCat/38ff645a-832a-4cdb-b089-a30bf54c3ad1.png": ("🪓", chat_id_1),
            "/docs/Images/BetCat/7ccfc1af-a691-4c5a-ae83-ad92b23a2d23.png": ("🦖", chat_id_1),
            "/docs/Images/BetCat/d3b363b2-4d69-4d0d-ae83-86ae0766203f.png": ("🥬", chat_id_1),
            "/docs/Images/BetCat/67773161-bcfc-4fb2-b8d3-dada09f50b30.png": ("👑", chat_id_1),
   
        }
        

    

    #drivers
    def _init_driver(self):
        options = Options()
        #options.add_argument('--user-data-dir=C:\\Users\\stefa\\AppData\\Local\\Google\\Chrome\\User Data')
        #options.add_argument('--profile-directory=Default')
        options.binary_location = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        
        service = Service(executable_path=self.driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.maximize_window()

        driver.execute_script("window.open('https://www.example.com', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])

        # DevTools Protocol για να ανοίξει το settings page
        driver.execute_cdp_cmd('Page.navigate', {'url': 'chrome://settings/content/javascript'})
        
        driver.switch_to.window(driver.window_handles[0])

        return driver
    
    #cookies
    #----------------------
    def wait_for_login(self, timeout=60):
        print("🔐 Περιμένω να κάνεις login στο site...")

        # Περιμένει να συνδεθείς για να σώσει τα cookies
        WebDriverWait(self.driver, timeout).until_not(lambda d: self.is_logged_out())
        print("✅ Login εντοπίστηκε! Αποθηκεύω cookies.")
        time.sleep(1)
        cookies = self.refresh_cookies()  # αποθηκεύει και επιστρέφει
        return cookies

    def refresh_cookies(self):
        cookies = self.driver.get_cookies()
        with open(self.cookies_file, "w") as f:
            json.dump(cookies, f)
        return cookies
    
    def load_cookies(self):
        if os.path.exists(self.cookies_file):
            with open(self.cookies_file, "r") as f:
                return json.load(f)
        return []
    
    #----------------------

    #id check

    def load_sent_ids(self):
        if not os.path.exists(self.sent_ids_file):
            return set()
        with open(self.sent_ids_file, "r") as f:
            return set(line.strip() for line in f.readlines())

    def save_sent_id(self, bet_id, max_ids=100):
        ids = self.load_sent_ids()
        ids.add(bet_id)
        trimmed = list(ids)[-max_ids:]
        with open(self.sent_ids_file, "w") as f:
            for _id in trimmed:
                f.write(f"{_id}\n")

    def get_chat_id_from_src(self, src):
        return self.emoji_sources.get(src, (None, None))[1]

    def get_emoji_from_src(self, src):
        return self.emoji_sources.get(src, (None, None))[0]

        
    def sync_ids_with_site(self, current_ticket_ids, sent_ids_file="json/sent_ids.txt", screenshots_folder="screenshots"):
        """
        Διαγράφει screenshots και IDs που δεν υπάρχουν πλέον στο site.
        """
        
        if not os.path.exists(sent_ids_file):
            return

        with open(sent_ids_file, "r") as f:
            stored_ids = set(line.strip() for line in f if line.strip())

        obsolete_ids = stored_ids - set(current_ticket_ids)


        if not obsolete_ids:
            return

        for obsolete_id in obsolete_ids:
            screenshot_path = os.path.join(screenshots_folder, f"ticket_{obsolete_id}.png")
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)
                print(f"🗑️ Διαγράφηκε screenshot για ID: {obsolete_id}")

        with open(sent_ids_file, "w") as f:
            for valid_id in stored_ids - obsolete_ids:
                f.write(f"{valid_id}\n")


    def auto_login(self, email, password):
        """
        Αυτόματη συμπλήρωση των στοιχείων σύνδεσης όταν εμφανίζεται η σελίδα login.
        """
        try:
            print("🔄 Προσπάθεια αυτόματης συμπλήρωσης στοιχείων σύνδεσης...")

            # Περιμένουμε να φορτωθούν τα input πεδία
            email_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "Email"))
            )
            password_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "Password"))
            )

            # Συμπλήρωση των πεδίων
            email_input.clear()
            email_input.send_keys(email)
            print("📧 Email συμπληρώθηκε.")

            password_input.clear()
            password_input.send_keys(password)
            print("🔐 Κωδικός συμπληρώθηκε.")

        except Exception as e:
            print(f"❌ Σφάλμα στην αυτόματη συμπλήρωση: {e}")           

    def is_logged_out(self):
        try:
            body = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            return any(word in body for word in ["login", "σύνδεση", "log in", "sign in"])
        except:
            return False

    def send_disconnected_message(self):
        message = "⚠️ Ο λογαριασμός blade.bet είναι αποσυνδεδεμένος."
        requests.post(
            f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
            data={"chat_id": self.chat_id_disconnected, "text": message},
            timeout=5
        )

    def save_base64_image(self, img_element, ticket_id):
        """
        Κατεβάζει την εικόνα είτε είναι base64 είτε απλό URL.
        """
        # Παίρνουμε το src attribute από το <img>
        img_src = img_element.get_attribute("src")
        
        if not img_src:
            print(f"❌ Δεν βρέθηκε το src στο στοιχείο για ticket ID: {ticket_id}")
            return
        
        # Δημιουργία ονόματος αρχείου με timestamp και ticket_id
        filename = f"screenshots/ticket_{ticket_id}.png"
        
        # Αν η εικόνα είναι base64
        if img_src.startswith("data:image"):
            print("🟢 Found Base64 image, decoding...")
            base64_data = img_src.split(",")[1]
            with open(filename, "wb") as file:
                file.write(base64.b64decode(base64_data))
            print(f"✅ Εικόνα αποθηκεύτηκε στο {filename}")

        # Αν η εικόνα είναι URL
        else:
            print("🟢 Found image URL, downloading...")
            
            # Αν είναι σχετικό URL, κάνουμε πλήρες path
            full_url = img_src if img_src.startswith("http") else urljoin("https://blade.bet", img_src)
            print(f"🔗 URL Λήψης: {full_url}")
            
            # Κατέβασμα της εικόνας
            try:
                response = requests.get(full_url, stream=True, timeout=5)
                if response.status_code == 200:
                    with open(filename, "wb") as file:
                        for chunk in response.iter_content(1024):
                            file.write(chunk)
                    print(f"✅ Εικόνα αποθηκεύτηκε στο {filename}")
                else:
                    print(f"❌ Σφάλμα λήψης εικόνας: {response.status_code}")
            except requests.RequestException as e:
                print(f"❌ Σφάλμα σύνδεσης κατά τη λήψη της εικόνας: {e}")

    
    def check_and_send_tickets(self):

        try:
            self.driver.get(self.url)
                
            if self.is_logged_out():
                # Προσπάθεια αυτόματης σύνδεσης
                self.auto_login("sidiropoulosspanos@gmail.com", "GamwTonArgy")
                while self.is_logged_out():
                    print("❗ Αποσύνδεση από blade.bet")
                    self.send_disconnected_message()
                    time.sleep(1)     
                
                self.was_logged_out = True
                self.wait_for_login()
                return
            else:
                self.was_logged_out = False  # reset αν είμαστε συνδεδεμένοι


            tickets = self.driver.find_elements(By.CLASS_NAME, "bet-item")
            current_ticket_ids = []

            if not tickets:
                print("⏸️ Δεν υπάρχουν δελτία.")
                self.sync_ids_with_site(current_ticket_ids)
                return

            sent_ids = self.load_sent_ids()
            os.makedirs("screenshots", exist_ok=True)
            new_found = False
            

            for ticket in tickets:
                try:
                    img = ticket.find_element(By.CLASS_NAME, "bet-image")
                    bet_id = img.get_attribute("data-imgbet-id")
                    current_ticket_ids.append(bet_id)
                    print("🧪 Εντοπίστηκε bet_id:", bet_id)

                    if not bet_id or bet_id in sent_ids:
                        continue
                    
                    # Αποθήκευση εικόνας κατευθείαν από base64
                    self.save_base64_image(img, bet_id)
                
                    # Ανάκτηση του src από το bet_cat_img
                    try:
                        bet_cat_img = ticket.find_element(By.CLASS_NAME, "bet_cat_img")
                        src = bet_cat_img.get_attribute("src")
                    except:
                        src = ""

                    # Αντιστοίχιση chat ID βάσει του src
                    parsed_src = urlparse(src).path
                    chat_id = self.get_chat_id_from_src(parsed_src)
                    emoji = self.get_emoji_from_src(parsed_src)




                    # Αποστολή της μεγάλης εικόνας στο Telegram
                    with open(f"screenshots/ticket_{bet_id}.png", "rb") as photo:
                        res = requests.post(
                            f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto",
                            data={"chat_id": chat_id},
                            files={"photo": photo}, # Στέλνουμε την μεγάλη εικόνα
                            timeout=5
                        )

                    if res.status_code == 200:
                        print(f"📤 Στάλθηκε δελτίο {bet_id}")
                        self.save_sent_id(bet_id)
                        new_found = True
                        emoji = self.get_emoji_from_src(urlparse(src).path)
                        if emoji:
                            requests.post(
                                url=f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
                                data={"chat_id": chat_id, "text": emoji},
                                timeout=5
                            )
                    else:
                        print(f"❌ Σφάλμα αποστολής ({bet_id}): {res.status_code}")

                    time.sleep(0.5)

                except Exception as e:
                    print(f"⚠️ Σφάλμα στο δελτίο: {e}")

            if not new_found:
                print("⏸️ Δεν βρέθηκαν νέα δελτία.")
                self.sync_ids_with_site(current_ticket_ids)

        except Exception as e:
            print(f"❌ Γενικό σφάλμα: {e}")
            traceback.print_exc()
