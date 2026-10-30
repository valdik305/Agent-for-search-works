import asyncio

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import TG_API_HASH, TG_API_ID


async def main():
    c = TelegramClient("tg_session", TG_API_ID, TG_API_HASH)
    await c.connect()
    if not await c.is_user_authorized():
        qr = await c.qr_login()
        while True:
            q = qrcode.QRCode(border=1)
            q.add_data(qr.url)
            q.print_ascii(invert=True)
            print("На телефоне: Telegram → Настройки → Устройства → Подключить устройство → наведите камеру на QR")
            try:
                await qr.wait(30)
                break
            except asyncio.TimeoutError:
                await qr.recreate()  # QR живёт ~30 секунд, обновляем
            except SessionPasswordNeededError:
                await c.sign_in(password=input("Пароль двухфакторной защиты: "))
                break
    me = await c.get_me()
    if me.bot:
        raise SystemExit("Вошли как бот. Удалите tg_session.session и повторите.")
    print("Вошли как:", me.first_name, me.id)
    await c.disconnect()


asyncio.run(main())