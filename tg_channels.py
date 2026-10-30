import asyncio
import logging

from telethon import TelegramClient

import db
from config import TG_API_HASH, TG_API_ID, TG_CHANNELS

log = logging.getLogger("tg")
client = None


async def start() -> bool:
    """Клиент создаётся внутри работающего цикла, иначе будет ошибка 'different loop'."""
    global client
    if not (TG_API_ID and TG_API_HASH and TG_CHANNELS):
        return False
    client = TelegramClient("tg_session", TG_API_ID, TG_API_HASH, receive_updates=False)
    try:
        await asyncio.wait_for(client.connect(), timeout=60)
        if not await client.is_user_authorized():
            log.warning("Telethon не авторизован. Запусти один раз: python tg_login.py")
            return False
        return True
    except Exception as e:
        log.warning("Не удалось подключить Telethon: %s", e)
        return False


async def fetch_new(known) -> list[dict]:
    if not (client and TG_CHANNELS and client.is_connected()):
        return []
    out = []
    for ch in TG_CHANNELS:
        try:
            last = int(db.kv_get(f"tg_last:{ch}", "0"))
            max_id = last
            kwargs = {"min_id": last, "limit": 50} if last else {"limit": 20}
            async for m in client.iter_messages(ch, **kwargs):
                max_id = max(max_id, m.id)
                text = (m.message or "").strip()
                uid = f"tg:{ch}:{m.id}"
                if len(text) < 40 or known(uid):
                    continue
                out.append(
                    {
                        "uid": uid,
                        "source": "tg",
                        "title": text.split("\n", 1)[0][:100],
                        "company": f"@{ch}",
                        "url": f"https://t.me/{ch}/{m.id}",
                        "text": text[:6000],
                    }
                )
            db.kv_set(f"tg_last:{ch}", str(max_id))
        except Exception as e:
            log.warning("tg channel %s error: %s", ch, e)
    return out