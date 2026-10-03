# Hisobchi bot (1-bosqich: matnli kirim-chiqim)

## Ishga tushirish
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # BOT_TOKEN va ANTHROPIC_API_KEY ni to'ldiring
python bot.py
```

## Ma'lumotlar saqlanishi
Hamma yozuv `DB_PATH` dagi SQLite faylida (standart `data/hisobchi.db`) saqlanadi.
Bot qayta ishga tushsa ham ma'lumot yo'qolmaydi. Serverda:
- `data/` papkasi doimiy diskda bo'lsin (Docker bo'lsa volume sifatida ulang);
- kunlik zaxira nusxa (cron), masalan:
  `0 3 * * * sqlite3 /yo'l/data/hisobchi.db ".backup '/yo'l/backup/hisobchi-$(date +\%F).db'"`

## Keyingi bosqichlar
2. Chek rasmini o'qish  3. Ovozli xabar  4. Mini App dashboard  5. Serverga joylash
