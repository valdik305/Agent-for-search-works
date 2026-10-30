import asyncio
import html
import logging
import time

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import hh
import scorer
import tg_channels
from config import (BOT_TOKEN, CHECK_INTERVAL_MIN, DAILY_APPLY_LIMIT, HH_RESUME_ID,
                    HH_TOKEN, MIN_SCORE, OWNER_ID)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("bot")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.message.filter(F.from_user.id == OWNER_ID)
dp.callback_query.filter(F.from_user.id == OWNER_ID)

esc = html.escape
CAN_HH_APPLY = bool(HH_TOKEN and HH_RESUME_ID)


def card(v) -> str:
    src = {"hh": "hh.ru", "tg": "Telegram"}.get(v["source"], v["source"])
    return (
        f"<b>{esc(v['title'])}</b>\n"
        f"{esc(v['company'])} · {src}\n"
        f"⭐ {v['score']}/10: {esc(v['reason'] or '')}\n"
        f"{esc(v['url'])}"
    )


def card_kb(rid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Письмо", callback_data=f"letter:{rid}"),
             InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip:{rid}")],
            [InlineKeyboardButton(text="✅ Откликнулся сам", callback_data=f"done:{rid}")],
        ]
    )


def letter_kb(rid: int, source: str) -> InlineKeyboardMarkup:
    rows = []
    if source == "hh" and CAN_HH_APPLY:
        rows.append([InlineKeyboardButton(text="🚀 Отправить на hh", callback_data=f"send:{rid}")])
    rows.append(
        [InlineKeyboardButton(text="🔁 Другое письмо", callback_data=f"letter:{rid}"),
         InlineKeyboardButton(text="✅ Откликнулся сам", callback_data=f"done:{rid}")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("Агент работает. Новые подходящие вакансии буду присылать сюда.\n/stats: статистика\n/check: проверить сейчас")


@dp.message(Command("stats"))
async def stats(m: Message):
    s = db.stats()
    lines = [f"{k}: {v}" for k, v in sorted(s.items())] or ["пока пусто"]
    await m.answer("<b>Статистика</b>\n" + "\n".join(lines))


@dp.message(Command("check"))
async def check_now(m: Message):
    n = await run_once()
    await m.answer(f"Готово. Новых подходящих: {n}")


@dp.message(Command("test"))
async def test_card(m: Message):
    v = {
        "uid": f"test:{time.time()}", "source": "hh",
        "title": "Тестовая вакансия: Python-разработчик (удалённо)",
        "company": "Тестовая компания", "url": "https://hh.ru",
        "text": "Нужен junior Python, aiogram, Telegram-боты. Удалённо.",
    }
    rid = db.add(v, 8, "проверка работы бота", "test")
    await m.answer(card(db.get(rid)), reply_markup=card_kb(rid))


@dp.callback_query(F.data.startswith("letter:"))
async def on_letter(cb: CallbackQuery):
    rid = int(cb.data.split(":")[1])
    v = db.get(rid)
    await cb.answer("Пишу письмо…")
    text = await scorer.letter(v["text"])
    if text.startswith(("⚠️", "Не задан")):
        # ошибка — НЕ сохраняем в БД, показываем как есть
        await cb.message.answer(f"<pre>{esc(text)}</pre>")
        return
    db.set_letter(rid, text)
    await cb.message.answer(f"<b>Письмо:</b>\n<pre>{esc(text)}</pre>", reply_markup=letter_kb(rid, v["source"]))

@dp.callback_query(F.data.startswith("skip:"))
async def on_skip(cb: CallbackQuery):
    db.set_status(int(cb.data.split(":")[1]), "skipped")
    await cb.answer("Пропущено")
    await cb.message.edit_reply_markup(reply_markup=None)


@dp.callback_query(F.data.startswith("done:"))
async def on_done(cb: CallbackQuery):
    db.set_status(int(cb.data.split(":")[1]), "applied_manual")
    await cb.answer("Записал")
    await cb.message.edit_reply_markup(reply_markup=None)


@dp.callback_query(F.data.startswith("send:"))
async def on_send(cb: CallbackQuery):
    rid = int(cb.data.split(":")[1])
    v = db.get(rid)

    # 1. Проверка, что письмо нормальное (твоя новая защита)
    if not v["letter"] or v["letter"].startswith(("⚠️", "Ошибка", "Не задан")):
        await cb.answer("Сначала сгенерируй нормальное письмо", show_alert=True)
        return

    # 2. Проверка дневного лимита откликов (твоя старая защита)
    if db.count_today("applied_hh") >= DAILY_APPLY_LIMIT:
        await cb.answer(f"Дневной лимит {DAILY_APPLY_LIMIT} откликов исчерпан", show_alert=True)
        return

    vid = v["uid"].split(":", 1)[1]
    ok, err = await hh.apply(vid, v["letter"] or "")
    if ok:
        db.set_status(rid, "applied_hh")
        await cb.answer("Отклик отправлен ✅")
        await cb.message.edit_reply_markup(reply_markup=None)
    else:
        await cb.answer("Не получилось", show_alert=True)
        await cb.message.answer(f"Ошибка hh.ru: <code>{esc(err)}</code>")


async def run_once() -> int:
    items = await hh.fetch_new(db.exists)          # пока можно оставить, но он 403
    items += await tg_channels.fetch_new(db.exists)
    sent = 0
    for v in items:
        if not scorer.passes(v["text"]):
            db.add(v, 0, "отсеяно по ключевым словам", "filtered")
            continue
        sc, reason = await scorer.score(v["text"])
        await asyncio.sleep(7)                     # ← 10 RPM = 6 сек, 7 с запасом
        if sc < MIN_SCORE:
            db.add(v, sc, reason, "low")
            continue
        rid = db.add(v, sc, reason, "sent")
        await bot.send_message(OWNER_ID, card(db.get(rid)), reply_markup=card_kb(rid),
                               disable_web_page_preview=True)
        sent += 1
        await asyncio.sleep(0.5)
    log.info("collected=%d sent=%d", len(items), sent)
    return sent


async def poll_loop():
    while True:
        try:
            await run_once()
        except Exception:
            log.exception("run_once failed")
        await asyncio.sleep(CHECK_INTERVAL_MIN * 60)


async def main():
    if await tg_channels.start():
        log.info("Telethon подключён")
    asyncio.create_task(poll_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
