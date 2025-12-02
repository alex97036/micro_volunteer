from pathlib import Path
from db import get_conn


def init_schema():
    # 專案根目錄 = backend 上一層
    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "sql" / "schema.sql"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)

    print("✅ Schema created / reset on database 'micro_volunteer'")


if __name__ == "__main__":
    init_schema()