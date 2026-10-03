"""Doimiy saqlash: barcha kirim-chiqimlar SQLite faylida saqlanadi.

Fayl joyi DB_PATH orqali belgilanadi (standart: data/hisobchi.db).
Serverda bu papka doimiy diskda (volume) turishi kerak.
"""
import os

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "data/hisobchi.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    kind        TEXT    NOT NULL CHECK (kind IN ('income', 'expense')),
    amount      INTEGER NOT NULL CHECK (amount > 0),
    category    TEXT    NOT NULL,
    note        TEXT    NOT NULL DEFAULT '',
    tx_date     TEXT    NOT NULL,
    source      TEXT    NOT NULL DEFAULT 'text',
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tx_user_date ON transactions (user_id, tx_date);
"""


async def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SCHEMA)
        await db.commit()


async def add_transactions(user_id: int, items: list[dict], source: str = "text") -> list[int]:
    ids = []
    async with aiosqlite.connect(DB_PATH) as db:
        for it in items:
            cur = await db.execute(
                "INSERT INTO transactions (user_id, kind, amount, category, note, tx_date, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, it["kind"], it["amount"], it["category"], it.get("note", ""), it["date"], source),
            )
            ids.append(cur.lastrowid)
        await db.commit()
    return ids


async def summary(user_id: int, date_from: str, date_to: str) -> dict:
    """Davr bo'yicha jami kirim/chiqim va chiqimlarning kategoriya bo'yicha taqsimoti."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT kind, COALESCE(SUM(amount), 0) FROM transactions "
            "WHERE user_id = ? AND tx_date BETWEEN ? AND ? GROUP BY kind",
            (user_id, date_from, date_to),
        )
        totals = {"income": 0, "expense": 0}
        for kind, total in await cur.fetchall():
            totals[kind] = total

        cur = await db.execute(
            "SELECT category, SUM(amount) AS s FROM transactions "
            "WHERE user_id = ? AND kind = 'expense' AND tx_date BETWEEN ? AND ? "
            "GROUP BY category ORDER BY s DESC",
            (user_id, date_from, date_to),
        )
        by_category = await cur.fetchall()
    return {"income": totals["income"], "expense": totals["expense"], "by_category": by_category}


async def recent(user_id: int, limit: int = 10) -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, tx_date, kind, amount, category, note FROM transactions "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return await cur.fetchall()


async def delete_last(user_id: int) -> tuple | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, tx_date, kind, amount, category, note FROM transactions "
            "WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = await cur.fetchone()
        if row:
            await db.execute("DELETE FROM transactions WHERE id = ?", (row[0],))
            await db.commit()
        return row
