"""Claude yordamida erkin matnni tuzilgan kirim/chiqim yozuvlariga aylantirish."""
import json
import os
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from anthropic import AsyncAnthropic

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tashkent"))

EXPENSE_CATS = [
    "Oziq-ovqat", "Restoran/kafe", "Transport", "Uy-joy", "Kommunal", "Aloqa",
    "Kiyim", "Salomatlik", "Ta'lim", "Ko'ngilochar", "Sovg'a", "Biznes xarajati", "Boshqa",
]
INCOME_CATS = ["Oylik", "Biznes daromadi", "Qarz qaytdi", "Sovg'a", "Boshqa"]

SYSTEM = """Sen hisobchi yordamchisan. Foydalanuvchi xabaridan kirim va chiqimlarni ajratib ol.
Bugungi sana: __TODAY__.

Faqat quyidagi JSON ko'rinishida javob ber, boshqa hech narsa yozma:
{"transactions": [{"kind": "expense" yoki "income", "amount": butun son, "category": "...", "note": "qisqa izoh", "date": "YYYY-MM-DD"}]}

Qoidalar:
- Summa so'mda, butun son. "20 ming" = 20000, "5 mln" = 5000000, "1.5 mln" = 1500000.
- Bir xabarda bir nechta yozuv bo'lishi mumkin, har birini alohida yoz.
- Sana aytilmasa bugungi sana. "kecha" = bugundan 1 kun oldin.
- Chiqim kategoriyalari: __EXP__
- Kirim kategoriyalari: __INC__
- Mos kelmasa "Boshqa" ni ishlat.
- Agar xabarda pul bilan bog'liq hech narsa bo'lmasa: {"transactions": []}
"""

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()  # ANTHROPIC_API_KEY muhit o'zgaruvchisidan oladi
    return _client


def _validate(items: list, today: str) -> list[dict]:
    clean = []
    for it in items:
        try:
            kind = it["kind"]
            amount = int(it["amount"])
            if kind not in ("income", "expense") or amount <= 0:
                continue
            allowed = EXPENSE_CATS if kind == "expense" else INCOME_CATS
            category = it.get("category") if it.get("category") in allowed else "Boshqa"
            try:
                tx_date = date.fromisoformat(str(it.get("date", today))).isoformat()
            except ValueError:
                tx_date = today
            clean.append(
                {
                    "kind": kind,
                    "amount": amount,
                    "category": category,
                    "note": str(it.get("note", ""))[:200],
                    "date": tx_date,
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return clean


async def parse_text(text: str) -> list[dict]:
    today = datetime.now(TZ).date().isoformat()
    system = (
        SYSTEM.replace("__TODAY__", today)
        .replace("__EXP__", ", ".join(EXPENSE_CATS))
        .replace("__INC__", ", ".join(INCOME_CATS))
    )
    resp = await _get_client().messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": text}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text")
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    data = json.loads(raw)
    return _validate(data.get("transactions", []), today)
