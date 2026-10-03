import asyncio
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()  # ai.py va db.py import qilinishidan oldin .env ni yuklaymiz

from aiogram import Bot, Dispatcher, F  # noqa: E402
from aiogram.filters import Command, CommandStart  # noqa: E402
from aiogram.types import Message  # noqa: E402

import db  # noqa: E402
from ai import TZ, parse_text  # noqa: E402

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
# Ixtiyoriy: faqat shu foydalanuvchilar ishlata oladi (vergul bilan ID lar)
ALLOWED = {int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x.strip()}

dp = Dispatcher()

HELP = (
    "Salom! Men hisobchi botman.\n\n"
    "Kirim yoki chiqimni oddiy so'z bilan yozing:\n"
    "• bugun nonushtaga 35 ming\n"
    "• taksi 20 ming, non 8 ming\n"
    "• oylik 5 mln tushdi\n\n"
    "Buyruqlar:\n"
    "/bugun - bugungi hisobot\n"
    "/hafta - oxirgi 7 kun\n"
    "/oy - joriy oy\n"
    "/oxirgi - oxirgi 10 ta yozuv\n"
    "/ochirish - oxirgi yozuvni o'chirish"
)


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def allowed(m: Message) -> bool:
    return not ALLOWED or (m.from_user and m.from_user.id in ALLOWED)


def today_local():
    return datetime.now(TZ).date()


async def send_report(m: Message, title: str, d_from, d_to) -> None:
    s = await db.summary(m.from_user.id, d_from.isoformat(), d_to.isoformat())
    balance = s["income"] - s["expense"]
    sign = "+" if balance >= 0 else "-"
    lines = [
        f"📊 {title} ({d_from.isoformat()} - {d_to.isoformat()})",
        f"Kirim: {fmt(s['income'])} so'm",
        f"Chiqim: {fmt(s['expense'])} so'm",
        f"Qoldiq: {sign}{fmt(abs(balance))} so'm",
    ]
    if s["by_category"]:
        lines.append("\nChiqimlar kategoriya bo'yicha:")
        for cat, total in s["by_category"]:
            pct = round(total * 100 / s["expense"]) if s["expense"] else 0
            lines.append(f"• {cat}: {fmt(total)} ({pct}%)")
    await m.answer("\n".join(lines))


@dp.message(CommandStart())
@dp.message(Command("help"))
async def cmd_start(m: Message):
    if allowed(m):
        await m.answer(HELP)


@dp.message(Command("bugun"))
async def cmd_today(m: Message):
    if allowed(m):
        t = today_local()
        await send_report(m, "Bugun", t, t)


@dp.message(Command("hafta"))
async def cmd_week(m: Message):
    if allowed(m):
        t = today_local()
        await send_report(m, "Oxirgi 7 kun", t - timedelta(days=6), t)


@dp.message(Command("oy"))
async def cmd_month(m: Message):
    if allowed(m):
        t = today_local()
        await send_report(m, "Joriy oy", t.replace(day=1), t)


@dp.message(Command("oxirgi"))
async def cmd_recent(m: Message):
    if not allowed(m):
        return
    rows = await db.recent(m.from_user.id, 10)
    if not rows:
        await m.answer("Hali yozuv yo'q.")
        return
    lines = ["Oxirgi yozuvlar:"]
    for _id, d, kind, amount, cat, note in rows:
        sign = "+" if kind == "income" else "-"
        extra = f" ({note})" if note else ""
        lines.append(f"{d} | {sign}{fmt(amount)} | {cat}{extra}")
    await m.answer("\n".join(lines))


@dp.message(Command("ochirish"))
async def cmd_delete_last(m: Message):
    if not allowed(m):
        return
    row = await db.delete_last(m.from_user.id)
    if not row:
        await m.answer("O'chirish uchun yozuv yo'q.")
        return
    _id, d, kind, amount, cat, _note = row
    sign = "+" if kind == "income" else "-"
    await m.answer(f"O'chirildi: {d} | {sign}{fmt(amount)} | {cat}")


@dp.message(F.text & ~F.text.startswith("/"))
async def on_text(m: Message):
    if not allowed(m):
        return
    await m.bot.send_chat_action(m.chat.id, "typing")
    try:
        items = await parse_text(m.text)
    except Exception:
        logging.exception("AI parse xatosi")
        await m.answer("Xabarni qayta ishlashda xatolik bo'ldi, birozdan keyin qayta urinib ko'ring.")
        return

    if not items:
        await m.answer("Pul bilan bog'liq ma'lumot topa olmadim. Masalan: \"taksi 20 ming\"")
        return

    await db.add_transactions(m.from_user.id, items, source="text")

    lines = ["✅ Saqlandi:"]
    for it in items:
        sign = "+" if it["kind"] == "income" else "-"
        extra = f" ({it['note']})" if it["note"] else ""
        lines.append(f"{it['date']} | {sign}{fmt(it['amount'])} so'm | {it['category']}{extra}")
    lines.append("\nNoto'g'ri bo'lsa: /ochirish")
    await m.answer("\n".join(lines))


async def main():
    await db.init_db()
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
