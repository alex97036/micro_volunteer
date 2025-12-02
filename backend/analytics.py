# backend/analytics.py
# 簡易 TinyDB 紀錄與分析：搜尋/瀏覽紀錄
from pathlib import Path
from datetime import datetime
from collections import Counter
import random

try:
    from tinydb import TinyDB
except ImportError as e:
    raise ImportError("請先安裝 tinydb: pip install tinydb") from e

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "analytics.json"

_db = TinyDB(DB_PATH)
_search_table = _db.table("search_logs")


def log_search(user_id: int, keyword: str, filters: dict, is_history: bool) -> None:
    """寫入搜尋紀錄"""
    _search_table.insert(
        {
            "ts": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": "search",
            "keyword": keyword or "",
            "filters": filters or {},
            "is_history": bool(is_history),
        }
    )


def top_keywords(limit: int = 10):
    """回傳熱門關鍵字 (非空)"""
    counter = Counter()
    for row in _search_table:
        kw = (row.get("keyword") or "").strip()
        if not kw:
            continue
        counter[kw] += 1
    return counter.most_common(limit)


def seed_dummy_logs(count: int = 50) -> None:
    """產生一些假的搜尋紀錄，方便測試"""
    keywords = ["海灘", "閱讀", "物資", "台南", "台中", "高雄", "物流", "First Aid", "Logistics", "Cleanup"]
    filters = [
        {"location": "台南"},
        {"location": "台中"},
        {"skill": "Logistics"},
        {"skill": "First Aid"},
        {"event_date": "2025-01-01"},
        {},
    ]

    for i in range(count):
        kw = random.choice(keywords)
        f = random.choice(filters)
        log_search(user_id=random.randint(1, 50), keyword=kw, filters=f, is_history=bool(i % 2))
