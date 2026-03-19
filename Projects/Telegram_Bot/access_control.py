# access_control.py
import json
import asyncio
import threading
from datetime import datetime
from typing import Iterable, Optional
from telethon.tl.types import ChannelParticipantsAdmins
from telethon import errors

from telethon.errors import FloodWaitError, ChatAdminRequiredError, UserNotParticipantError
from telethon.tl.types import ChatBannedRights, Channel, Chat
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import DeleteChatUserRequest


class AccessControl:
    """
    Periodic scanner που:
    - φορτώνει ΚΑΘΕ ΦΟΡΑ το user_data.json,
    - για κάθε group (παράλληλα) πετάει όποιον δεν είναι approved,
    - έχει ήπιο throttle για αποφυγή FloodWait.
    Περιέχει και unban_all_now για το approve flow.
    """

    def __init__(
        self,
        client,
        group_ids: Optional[Iterable[int]] = None,
        group_ids_file: str = "json/group_ids.json",
        user_data_file: str = "json/user_data.json",
        scan_interval_sec: int = 15,      # κάθε πόσο να γίνεται scan
        participant_batch_sleep: float = 0.0,  # ύπνος ανά participant (0 = off)
        per_action_sleep: float = 0.15,   # ύπνος μετά από κάθε kick/unban
        concurrency: int = 6,             # πόσα groups ταυτόχρονα
    ):
        self.client = client
        self._scan_task = None  # task handle
        # group ids
        if group_ids is not None:
            self.group_ids = sorted({int(g) for g in group_ids})
        else:
            with open(group_ids_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.group_ids = (
                [int(x) for x in data["group_ids"]]
                if isinstance(data, dict) and "group_ids" in data
                else [int(x) for x in data]
            )

        self.user_data_file = user_data_file
        self._admin_cache = {} 

        # ρυθμίσεις scan
        self.scan_interval_sec = scan_interval_sec
        self.participant_batch_sleep = participant_batch_sleep
        self.per_action_sleep = per_action_sleep
        self.concurrency = max(1, int(concurrency))


    # ---------------- helpers ----------------
    async def _get_admin_ids(self, gid: int):
        if gid in self._admin_cache:
            return self._admin_cache[gid]
        try:
            admins = await self.client.get_participants(gid, filter=ChannelParticipantsAdmins())
            ids = {int(a.id) for a in admins}
            self._admin_cache[gid] = ids
            return ids
        except Exception:
            return set()

    def _load_approved_ids(self) -> set[int]:
        """
        Διαβάζει ΚΑΘΕ ΦΟΡΑ το user_data.json και επιστρέφει τα approved ids.
        Αν υπάρχει end_date και έχει λήξει, τον θεωρούμε ΜΗ approved.
        """
        try:
            with open(self.user_data_file, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except Exception:
            return set()

        now = datetime.now()
        approved: set[int] = set()
        for k, info in data.items():
            if k == "total_members":
                continue
            try:
                uid = int(k)
            except (TypeError, ValueError):
                continue

            end = (info or {}).get("end_date")
            if end:
                try:
                    end_dt = datetime.strptime(end, "%d/%m/%Y %H:%M:%S")
                    if end_dt > now:
                        approved.add(uid)
                except ValueError:
                    # αν το format είναι περίεργο, θεωρούμε approved εφόσον υπάρχει στο json
                    approved.add(uid)
            else:
                # αν δεν έχει end_date, το θεωρούμε approved
                approved.add(uid)
        return approved

    async def _kick_one(self, gid: int, user) -> None:
        """
        Kick/ban από ένα group.
        ΔΕΧΕΤΑΙ user entity (ή id) αλλά πάντα το λύνει σε InputUser για EditBannedRequest.
        """
        try:
            entity = await self.client.get_entity(gid)

            # ΠΑΝΤΑ λύσε σε InputUser (ώστε να έχει access_hash)
            try:
                input_user = await self.client.get_input_entity(user)
            except Exception:
                # αν μας έδωσαν μόνο id, προσπάθησε να τον βρεις πρώτα στο group
                # (όταν έρχεται από iter_participants είναι ήδη entity, άρα θα περάσει)
                input_user = user  # τελευταία προσπάθεια

            if isinstance(entity, Channel):
                await self.client(
                    EditBannedRequest(
                        channel=entity,
                        participant=input_user,
                        banned_rights=ChatBannedRights(until_date=None, view_messages=True),
                    )
                )
            elif isinstance(entity, Chat):
                await self.client(DeleteChatUserRequest(chat_id=gid, user_id=input_user))
            else:
                # fallback σαν channel
                await self.client(
                    EditBannedRequest(
                        channel=gid,
                        participant=input_user,
                        banned_rights=ChatBannedRights(until_date=None, view_messages=True),
                    )
                )
            print(f"❌ Kicked {getattr(user, 'id', user)} from {gid}")
        except ChatAdminRequiredError:
            print(f"⚠️ No admin rights in {gid} to kick {getattr(user, 'id', user)}.")
        except errors.UserAdminInvalidError:
            # είναι admin που δεν προήγαγες → αγνόησε σιωπηλά
            return
        except errors.RPCError as e:
            msg = str(e).lower()
            if "tried to ban an admin" in msg or "not an admin" in msg:
                return  # αγνόησε αυτά τα γνωστά
            print(f"⚠️ Kick RPC error {getattr(user, 'id', user)} in {gid}: {e}")
        except FloodWaitError as fe:
            print(f"⏳ FloodWait on kick in {gid} for {getattr(fe, 'seconds', 0)}s (skipping).")
        except Exception as e:
            if "participant ID is invalid" in str(e):
                return
            print(f"⚠️ Kick error {getattr(user, 'id', user)} in {gid}: {e}")




    # ---------------- public: approve flow ----------------

    async def unban_all_now(self, uid: int) -> None:
        """Άμεσο unban σε ΟΛΑ τα groups. Αγνοεί τα λάθη/όπου δεν χρειάζεται."""
        rights_unban = ChatBannedRights(until_date=None, view_messages=False)
        print(f"✅ Immediate UNBAN for user {uid} in ALL groups")
        for gid in self.group_ids:
            try:
                await self.client(
                    EditBannedRequest(
                        channel=gid,
                        participant=uid,
                        banned_rights=rights_unban,
                    )
                )
                print(f"✔ Unbanned {uid} in {gid}")
            except (ChatAdminRequiredError, UserNotParticipantError):
                pass
            except FloodWaitError as fe:
                print(f"⏭ Skipping {gid} due to FloodWait {getattr(fe, 'seconds', 0)}s")
            except Exception as e:
                print(f"⏭ Unban skip {gid}: {e}")
            if self.per_action_sleep > 0:
                await asyncio.sleep(self.per_action_sleep)

    # ---------------- periodic scan ----------------

    async def _scan_group_once(self, gid: int, approved: set[int]) -> None:
        """
        Σκανάρει ΕΝΑ group: κικάρει όλους τους όχι-approved.
        Δεν κάνουμε get_permissions (εξοικονομούμε 1 API call/χρήστη).
        """
        try:
            # skip αν είναι admin/owner
            admin_ids = await self._get_admin_ids(gid)
            async for member in self.client.iter_participants(gid, limit=None, aggressive=True):
                uid = int(member.id)
                if getattr(member, "bot", False):
                    continue
                if uid in approved:
                    continue
                
                if uid in admin_ids:
                    continue  # αγνόησε admins/owners

                # όχι approved -> kick
                await self._kick_one(gid, member)


                if self.participant_batch_sleep > 0:
                    await asyncio.sleep(self.participant_batch_sleep)
        except ChatAdminRequiredError:
            print(f"⚠️ No admin rights to list participants in {gid}.")
        except FloodWaitError as fe:
            print(f"⏳ FloodWait on list participants {gid} for {getattr(fe, 'seconds', 0)}s.")
        except Exception as e:
            print(f"⚠️ scan_group error {gid}: {e}")

    async def _scan_once(self) -> None:
        approved = self._load_approved_ids()
        if not isinstance(approved, set):
            approved = set(approved)

        # περιορισμός ταυτόχρονων groups
        sem = asyncio.Semaphore(self.concurrency)

        async def worker(gid: int):
            async with sem:
                await self._scan_group_once(gid, approved)

        await asyncio.gather(*(worker(g) for g in self.group_ids))

    async def _scan_loop(self) -> None:
        print(f"🔁 AccessControl scan loop started (every {self.scan_interval_sec}s, {self.concurrency} groups in parallel).")
        while True:
            if not self.client.is_connected():
                # αν για οποιοδήποτε λόγο αποσυνδεθεί, περίμενε να επανέλθει
                await asyncio.sleep(1.0)
                continue
            try:
                await self._scan_once()
            except Exception as e:
                print(f"⚠️ scan loop error: {e}")
            await asyncio.sleep(self.scan_interval_sec)


    # --------- thread runner (ώστε να μην θες active event loop) ---------

    async def start_periodic_scan(self) -> None:
        """
        Ξεκινά το periodic scan μέσα στο ΙΔΙΟ event loop με τον Telethon client.
        Κάλεσέ το ΜΕΤΑ το client.start()/connect().
        """
        if self._scan_task and not self._scan_task.done():
            return

        # Περίμενε να είναι συνδεδεμένος ο client (για να αποφύγουμε "disconnected")
        while not self.client.is_connected():
            await asyncio.sleep(0.5)

        self._scan_task = asyncio.create_task(self._scan_loop())
        print("🟢 AccessControl periodic scanner started (task).")
