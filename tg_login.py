from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
from config import TG_API_HASH, TG_API_ID

c = TelegramClient("tg_session", TG_API_ID, TG_API_HASH)
c.connect()
if not c.is_user_authorized():
    phone = input("Ваш НОМЕР ТЕЛЕФОНА с + (не токен бота): ").strip()
    if not phone.startswith("+"):
        raise SystemExit("Номер должен начинаться с +, например +79991234567")
    c.send_code_request(phone)
    code = input("Код из Telegram: ").strip()
    try:
        c.sign_in(phone, code)
    except SessionPasswordNeededError:
        c.sign_in(password=input("Пароль двухфакторки: "))

me = c.get_me()
if me.bot:
    raise SystemExit("Вошли как бот. Удалите tg_session.session и повторите.")
print("Вошли как:", me.first_name, me.id)
c.disconnect()