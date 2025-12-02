# backend/organizer.py
from typing import List, Dict, Optional
from datetime import date
from db import get_conn
from volunteer import create_skill


def map_organizer_org(user_id: int, org_id: int) -> None:
    """建立 Organizer 與 ORG 的對應"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ORGANIZER_ORG (user_id, org_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, org_id) DO NOTHING;
                """,
                (user_id, org_id),
            )


def get_primary_org(user_id: int) -> int:
    """
    取得使用者的主要 ORG（取第一筆）。如果沒有，會 ValueError。
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT org_id
                FROM ORGANIZER_ORG
                WHERE user_id = %s
                ORDER BY org_id
                LIMIT 1;
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Organizer 尚未綁定任何 ORG")
            return row[0]


def get_or_create_default_org(user_id: int) -> int:
    """
    先找有無綁定的 ORG；沒有的話自動建一個以使用者名稱為名的 ORG 並綁定。
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT org_id
                FROM ORGANIZER_ORG
                WHERE user_id = %s
                ORDER BY org_id
                LIMIT 1;
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if row:
                return row[0]

            # 取 user 的名稱與 email
            cur.execute(
                'SELECT user_name, email FROM "USER" WHERE user_id = %s;',
                (user_id,),
            )
            user_row = cur.fetchone()
            if not user_row:
                raise ValueError(f"user_id {user_id} 不存在")
            user_name, email = user_row

            org_name = f"{user_name} Org"
            contact_email = email or f"{user_name}@example.org"

            cur.execute(
                """
                INSERT INTO ORG (org_name, contact_email)
                VALUES (%s, %s)
                RETURNING org_id;
                """,
                (org_name, contact_email),
            )
            org_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO ORGANIZER_ORG (user_id, org_id)
                VALUES (%s, %s);
                """,
                (user_id, org_id),
            )
            return org_id


def create_org(
    org_name: str, contact_email: str, owner_user_id: Optional[int] = None
) -> int:
    sql = """
        INSERT INTO ORG (org_name, contact_email)
        VALUES (%s, %s)
        RETURNING org_id;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (org_name, contact_email))
            org_id = cur.fetchone()[0]
            if owner_user_id is not None:
                cur.execute(
                    """
                    INSERT INTO ORGANIZER_ORG (user_id, org_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, org_id) DO NOTHING;
                    """,
                    (owner_user_id, org_id),
                )
    return org_id


def create_venue(name: str, address: str, capacity: int) -> int:
    sql = """
        INSERT INTO VENUE (name, address, capacity)
        VALUES (%s, %s, %s)
        RETURNING venue_id;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (name, address, capacity))
            venue_id = cur.fetchone()[0]
    return venue_id


def create_event(
    owner_id: int,
    org_id: Optional[int],
    venue_id: int,
    event_date: date,
    start_hour: int,
    end_hour: int,
    capacity: int,
    title: str,
    description: str,
    status: str = "Planned",
) -> int:
    if org_id is None:
        org_id = get_or_create_default_org(owner_id)
    duration_hours = end_hour - start_hour
    if duration_hours < 1 or duration_hours > 3:
        raise ValueError("活動時數必須介於 1~3 小時，請確認開始/結束時間")
    sql = """
        INSERT INTO TASK_EVENT
          (owner_id, org_id, venue_id,
           event_date, start_hour, end_hour, capacity, duration_hours,
           status, title, description)
        VALUES
          (%s, %s, %s,
           %s, %s, %s, %s, %s,
           %s, %s, %s)
        RETURNING event_id;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    owner_id,
                    org_id,
                    venue_id,
                    event_date,
                    start_hour,
                    end_hour,
                    capacity,
                    duration_hours,
                    status,
                    title,
                    description,
                ),
            )
            event_id = cur.fetchone()[0]
    return event_id


def set_event_periods(event_id: int, hours: List[int]) -> None:
    """
    設定任務時間（使用小時列表），會自動轉成 start/end/hour，並限制最多 3 小時
    （會先刪掉原本 TASK_EVENT_PERIOD 的設定）
    """
    if not hours:
        raise ValueError("至少需要一個時段")
    start_hour = min(hours)
    end_hour = max(hours) + 1
    duration_hours = end_hour - start_hour
    if duration_hours > 3:
        raise ValueError("活動時間最多 3 小時")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM TASK_EVENT_PERIOD WHERE event_id = %s;",
                (event_id,),
            )
            for h in hours:
                cur.execute(
                    """
                    INSERT INTO TASK_EVENT_PERIOD (event_id, period_hour)
                    VALUES (%s, %s);
                    """,
                    (event_id, h),
                )
            # 更新 TASK_EVENT 的開始/結束時間
            cur.execute(
                """
                UPDATE TASK_EVENT
                SET start_hour = %s,
                    end_hour = %s,
                    duration_hours = %s
                WHERE event_id = %s;
                """,
                (start_hour, end_hour, duration_hours, event_id),
            )
    return True


def set_required_skills(event_id: int, skill_weights: Dict[str, int]) -> None:
    """
    skill_weights: 例如 {"First Aid": 2, "Logistics": 1}
    會自動建立 SKILL，然後寫進 TASK_REQUIRED_SKILL
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 先清除舊設定
            cur.execute(
                "DELETE FROM TASK_REQUIRED_SKILL WHERE event_id = %s;",
                (event_id,),
            )

            for skill_name, weight in skill_weights.items():
                skill_id = create_skill(skill_name)
                cur.execute(
                    """
                    INSERT INTO TASK_REQUIRED_SKILL (event_id, skill_id, weight)
                    VALUES (%s, %s, %s);
                    """,
                    (event_id, skill_id, weight),
                )
    return True


def list_my_events(owner_id: int) -> List[Dict]:
    """列出該 Organizer 建立的任務與報名概況"""
    sql = """
        SELECT e.event_id,
               e.title,
               e.event_date,
               e.start_hour,
               e.end_hour,
               e.status,
               e.capacity,
               COALESCE(SUM(CASE WHEN p.status='Active' THEN 1 END),0) AS active_cnt,
               COALESCE(SUM(CASE WHEN p.status='Cancelled' THEN 1 END),0) AS cancelled_cnt,
               COALESCE(wl.wl_cnt, 0) AS waitlist_cnt
        FROM TASK_EVENT e
        LEFT JOIN PARTICIPATION p ON p.event_id = e.event_id
        LEFT JOIN (
            SELECT event_id, COUNT(*) AS wl_cnt
            FROM WAITLIST
            GROUP BY event_id
        ) wl ON wl.event_id = e.event_id
        WHERE e.owner_id = %s
        GROUP BY e.event_id, e.title, e.event_date, e.start_hour, e.end_hour,
                 e.status, e.capacity, wl.wl_cnt
        ORDER BY e.event_date DESC, e.event_id DESC;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (owner_id,))
            rows = cur.fetchall()
    return [
        {
            "event_id": r[0],
            "title": r[1],
            "event_date": r[2],
            "start_hour": r[3],
            "end_hour": r[4],
            "status": r[5],
            "capacity": r[6],
            "active": r[7],
            "cancelled": r[8],
            "waitlist": r[9],
        }
        for r in rows
    ]


def list_all_events_with_counts() -> List[Dict]:
    """列出所有任務與報名概況（Admin 用）"""
    sql = """
        SELECT e.event_id,
               e.title,
               e.event_date,
               e.start_hour,
               e.end_hour,
               e.status,
               e.capacity,
               COALESCE(SUM(CASE WHEN p.status='Active' THEN 1 END),0) AS active_cnt,
               COALESCE(SUM(CASE WHEN p.status='Cancelled' THEN 1 END),0) AS cancelled_cnt,
               COALESCE(wl.wl_cnt, 0) AS waitlist_cnt
        FROM TASK_EVENT e
        LEFT JOIN PARTICIPATION p ON p.event_id = e.event_id
        LEFT JOIN (
            SELECT event_id, COUNT(*) AS wl_cnt
            FROM WAITLIST
            GROUP BY event_id
        ) wl ON wl.event_id = e.event_id
        GROUP BY e.event_id, e.title, e.event_date, e.start_hour, e.end_hour,
                 e.status, e.capacity, wl.wl_cnt
        ORDER BY e.event_date DESC, e.event_id DESC;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return [
        {
            "event_id": r[0],
            "title": r[1],
            "event_date": r[2],
            "start_hour": r[3],
            "end_hour": r[4],
            "status": r[5],
            "capacity": r[6],
            "active": r[7],
            "cancelled": r[8],
            "waitlist": r[9],
        }
        for r in rows
    ]


def list_venues() -> List[Dict]:
    sql = """
        SELECT venue_id, name, address, capacity
        FROM VENUE
        ORDER BY venue_id;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return [
        {"venue_id": r[0], "name": r[1], "address": r[2], "capacity": r[3]}
        for r in rows
    ]


def list_skills() -> List[Dict]:
    sql = "SELECT skill_id, skill_name FROM SKILL ORDER BY skill_id;"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return [{"skill_id": r[0], "skill_name": r[1]} for r in rows]
