# backend/volunteer.py
from datetime import datetime, date
from db import get_conn
from typing import Optional, List, Dict

ALLOWED_ROLES = {"Volunteer", "Organizer", "Admin"}

# ---------- 1. 註冊使用者 ----------

def register_user(
    user_name: str,
    email: str,
    phone: int,
    password: str,
    role: str = "Volunteer",
) -> int:
    """
    建立一個新 user，並寫入預設角色，回傳 user_id
    """
    if role not in ALLOWED_ROLES:
        raise ValueError(f"無效的角色: {role}")

    sql = """
        INSERT INTO "USER" (user_name, email, phone, password)
        VALUES (%s, %s, %s, %s)
        RETURNING user_id;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_name, email, phone, password))
            user_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO USER_ROLE (user_id, role)
                VALUES (%s, %s)
                ON CONFLICT (user_id, role) DO NOTHING;
                """,
                (user_id, role),
            )
    return user_id


# ---------- 2. 技能相關 ----------

def create_skill(skill_name: str) -> int:
    """
    新增一個技能（例如: First Aid, Logistics），回傳 skill_id
    """
    sql = """
        INSERT INTO SKILL (skill_name)
        VALUES (%s)
        ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name
        RETURNING skill_id;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (skill_name,))
            skill_id = cur.fetchone()[0]
    return skill_id


def set_user_skill(user_id: int, skill_id: int, level: int) -> None:
    """
    設定使用者某個技能的等級（1~5），如果已存在就更新
    """
    sql = """
        INSERT INTO USER_SKILL (user_id, skill_id, level)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, skill_id)
        DO UPDATE SET level = EXCLUDED.level;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, skill_id, level))

def get_user_roles(user_id: int) -> List[str]:
    """查詢使用者的所有角色"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role FROM USER_ROLE WHERE user_id = %s;",
                (user_id,),
            )
            rows = cur.fetchall()
    return [r[0] for r in rows]


def user_has_role(user_id: int, role: str) -> bool:
    """確認使用者是否具備指定角色"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM USER_ROLE
                WHERE user_id = %s AND role = %s
                LIMIT 1;
                """,
                (user_id, role),
            )
            row = cur.fetchone()
    return row is not None


def normalize_role(role: str) -> str:
    """將輸入的角色轉成標準格式（首字大寫）"""
    if not role:
        return role
    role_std = role.strip().lower().capitalize()
    return role_std


def list_users_with_roles() -> List[Dict]:
    """
    列出所有使用者與角色（demo 用）
    """
    sql = """
        SELECT u.user_id, u.user_name, u.email,
               COALESCE(array_agg(r.role ORDER BY r.role), '{}') AS roles
        FROM "USER" u
        LEFT JOIN USER_ROLE r ON r.user_id = u.user_id
        GROUP BY u.user_id, u.user_name, u.email
        ORDER BY u.user_id;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    result: List[Dict] = []
    for row in rows:
        user_id, user_name, email, roles = row
        result.append(
            {
                "user_id": user_id,
                "user_name": user_name,
                "email": email,
                "roles": list(roles) if roles else [],
            }
        )
    return result


def add_role(target_user_id: int, role: str) -> None:
    role = normalize_role(role)
    if role not in ALLOWED_ROLES:
        raise ValueError(f"無效的角色: {role}")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO USER_ROLE (user_id, role)
                VALUES (%s, %s)
                ON CONFLICT (user_id, role) DO NOTHING;
                """,
                (target_user_id, role),
            )


def remove_role(target_user_id: int, role: str) -> None:
    role = normalize_role(role)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM USER_ROLE WHERE user_id = %s AND role = %s;",
                (target_user_id, role),
            )


def update_user_profile(
    user_id: int,
    user_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[int] = None,
    password: Optional[str] = None,
) -> None:
    """更新使用者基本資料（提供哪些欄位就更新哪些）"""
    fields = []
    params: List = []
    if user_name:
        fields.append("user_name = %s")
        params.append(user_name)
    if email:
        fields.append("email = %s")
        params.append(email)
    if phone is not None:
        fields.append("phone = %s")
        params.append(phone)
    if password:
        fields.append("password = %s")
        params.append(password)
    if not fields:
        return
    params.append(user_id)
    sql = f'UPDATE "USER" SET {", ".join(fields)} WHERE user_id = %s;'
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def mark_finished_events() -> int:
    """
    將已經結束的活動標記為 Finished
    規則：日期在今天之前，或今天且 end_hour <= 當前小時
    回傳更新筆數
    """
    now = datetime.now()
    today = now.date()
    current_hour = now.hour
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE TASK_EVENT
                SET status = 'Finished'
                WHERE status <> 'Finished'
                  AND (
                        event_date < %s
                        OR (event_date = %s AND end_hour <= %s)
                      );
                """,
                (today, today, current_hour),
            )
            return cur.rowcount


def get_event_participants(event_id: int) -> List[Dict]:
    """列出某任務的參與/候補狀況"""
    sql = """
        SELECT p.user_id, u.user_name, u.email, u.phone, p.role, p.status, p.join_time
        FROM PARTICIPATION p
        JOIN "USER" u ON u.user_id = p.user_id
        WHERE p.event_id = %s
        ORDER BY p.join_time;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (event_id,))
            rows = cur.fetchall()
    return [
        {
            "user_id": r[0],
            "user_name": r[1],
            "email": r[2],
            "phone": r[3],
            "role": r[4],
            "status": r[5],
            "join_time": r[6],
        }
        for r in rows
    ]


def get_venue_bookings(venue_id: int, on_date: date) -> List[Dict]:
    """查詢場地在指定日期的已預約時段"""
    sql = """
        SELECT event_id, title, start_hour, end_hour, status
        FROM TASK_EVENT
        WHERE venue_id = %s AND event_date = %s
        ORDER BY start_hour;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (venue_id, on_date))
            rows = cur.fetchall()
    return [
        {
            "event_id": r[0],
            "title": r[1],
            "start_hour": r[2],
            "end_hour": r[3],
            "status": r[4],
        }
        for r in rows
    ]


def is_venue_available(
    venue_id: int, on_date: date, start_hour: int, end_hour: int
) -> bool:
    """
    檢查場地在指定日期與時段是否可用
    規則：無任何重疊 (existing.start < new_end AND existing.end > new_start)
    """
    sql = """
        SELECT 1
        FROM TASK_EVENT
        WHERE venue_id = %s
          AND event_date = %s
          AND start_hour < %s
          AND end_hour   > %s
        LIMIT 1;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (venue_id, on_date, end_hour, start_hour))
            row = cur.fetchone()
    return row is None


# ---------- 3. 查詢任務（簡單版） ----------

def search_tasks(
    event_date: Optional[date] = None,
    location_keyword: Optional[str] = None,
    skill_keyword: Optional[str] = None,
    title_keyword: Optional[str] = None,
    only_available: bool = True,
    include_finished: bool = False,
    only_finished: bool = False,
    future_only: bool = False,
    past_only: bool = False,
) -> List[Dict]:
    """
    依照企劃書需求搜尋任務：
      - event_date: 指定日期 (None = 不限制)
      - location_keyword: 地點關鍵字 (venue.name / address, None = 不限制)
      - skill_keyword: 需要技能關鍵字 (None = 不限制)
      - only_available: True 時只顯示尚未額滿的任務

    回傳: 每個任務是一個 dict
    """
    sql = """
        SELECT
            e.event_id,
            e.title,
            e.event_date,
            e.start_hour,
            e.end_hour,
            e.status,
            v.name   AS venue_name,
            v.address,
            e.capacity,
            COALESCE(
              SUM(CASE WHEN p.status = 'Active' THEN 1 ELSE 0 END),
              0
            ) AS active_volunteers
        FROM TASK_EVENT e
        JOIN VENUE v
          ON v.venue_id = e.venue_id
        LEFT JOIN PARTICIPATION p
          ON p.event_id = e.event_id
        LEFT JOIN TASK_REQUIRED_SKILL trs
          ON trs.event_id = e.event_id
        LEFT JOIN SKILL s
          ON s.skill_id = trs.skill_id
        WHERE 1 = 1
    """

    conditions = []
    params: List = []

    if event_date is not None:
        conditions.append("e.event_date = %s")
        params.append(event_date)

    if location_keyword:
        conditions.append("(v.name ILIKE %s OR v.address ILIKE %s)")
        kw = f"%{location_keyword}%"
        params.extend([kw, kw])

    if skill_keyword:
        conditions.append("s.skill_name ILIKE %s")
        params.append(f"%{skill_keyword}%")

    if title_keyword:
        conditions.append("(e.title ILIKE %s OR e.description ILIKE %s)")
        kw = f"%{title_keyword}%"
        params.extend([kw, kw])

    if future_only:
        conditions.append("e.event_date >= %s")
        params.append(date.today())
    if past_only:
        conditions.append("e.event_date < %s")
        params.append(date.today())

    if only_finished:
        conditions.append("e.status = 'Finished'")
    elif not include_finished:
        conditions.append("e.status <> 'Finished'")

    if conditions:
        sql += " AND " + " AND ".join(conditions)

    sql += """
        GROUP BY
            e.event_id, e.title, e.event_date, e.start_hour, e.end_hour, e.status,
            v.name, v.address, e.capacity
        ORDER BY e.event_date, e.event_id;
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    results: List[Dict] = []
    for row in rows:
        (
            event_id,
            title,
            ev_date,
            start_hour,
            end_hour,
            status,
            venue_name,
            address,
            capacity,
            active_vols,
        ) = row

        active_vols = active_vols or 0
        slots_left = capacity - active_vols

        # 如果只看「尚未額滿」的任務，且已滿 → skip
        if only_available and slots_left <= 0:
            continue

        results.append(
            {
                "event_id": event_id,
                "title": title,
                "date": ev_date,
                "start_hour": start_hour,
                "end_hour": end_hour,
                "status": status,
                "venue": venue_name,
                "address": address,
                "capacity": capacity,
                "active_volunteers": active_vols,
                "slots_left": slots_left,
            }
        )

    return results


def get_user_history(user_id: int) -> List[Dict]:
    """
    依企劃書：查詢某位志工所有參與過的任務
    （包含 Active / Cancelled）
    """
    sql = """
        SELECT
            e.event_id,
            e.title,
            e.event_date,
            v.name   AS venue_name,
            v.address,
            p.role,
            p.status,
            p.join_time
        FROM PARTICIPATION p
        JOIN TASK_EVENT e
          ON e.event_id = p.event_id
        JOIN VENUE v
          ON v.venue_id = e.venue_id
        WHERE p.user_id = %s
        ORDER BY e.event_date DESC, p.join_time DESC;
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            rows = cur.fetchall()

    history: List[Dict] = []
    for row in rows:
        (
            event_id,
            title,
            ev_date,
            venue_name,
            address,
            role,
            status,
            join_time,
        ) = row

        history.append(
            {
                "event_id": event_id,
                "title": title,
                "date": ev_date,
                "venue": venue_name,
                "address": address,
                "role": role,
                "status": status,
                "join_time": join_time,
            }
        )

    return history


def get_user_active_participation(user_id: int) -> List[Dict]:
    """查詢使用者目前已報名且狀態為 Active 的任務"""
    sql = """
        SELECT
            e.event_id,
            e.title,
            e.event_date,
            e.start_hour,
            e.end_hour,
            v.name   AS venue_name,
            v.address,
            p.join_time
        FROM PARTICIPATION p
        JOIN TASK_EVENT e ON e.event_id = p.event_id
        JOIN VENUE v ON v.venue_id = e.venue_id
        WHERE p.user_id = %s
          AND p.status = 'Active'
        ORDER BY e.event_date, e.start_hour;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            rows = cur.fetchall()
    return [
        {
            "event_id": r[0],
            "title": r[1],
            "date": r[2],
            "start_hour": r[3],
            "end_hour": r[4],
            "venue": r[5],
            "address": r[6],
            "join_time": r[7],
        }
        for r in rows
    ]

# ---------- 4. 報名任務 (含候補) ----------

def join_task(user_id: int, event_id: int) -> str:
    """
    報名任務：
      - 若名額未滿 -> 寫入 PARTICIPATION.status='Active'
      - 若名額已滿 -> 寫入 WAITLIST，position=最大+1
    回傳字串：'joined' 或 'waitlisted'
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 鎖住該 event，避免並發超額
            cur.execute(
                "SELECT capacity FROM TASK_EVENT WHERE event_id = %s FOR UPDATE;",
                (event_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"event_id {event_id} not found")
            capacity = row[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM PARTICIPATION
                WHERE event_id = %s AND status = 'Active';
                """,
                (event_id,),
            )
            active_count = cur.fetchone()[0]

            now = datetime.now()

            if active_count < capacity:
                # 直接加入 PARTICIPATION
                cur.execute(
                    """
                    INSERT INTO PARTICIPATION (user_id, event_id, join_time, role, status)
                    VALUES (%s, %s, %s, 'Volunteer', 'Active')
                    ON CONFLICT (user_id, event_id)
                    DO UPDATE SET status = 'Active', join_time = EXCLUDED.join_time;
                    """,
                    (user_id, event_id, now),
                )
                return "joined"
            else:
                # 加入 WAITLIST
                cur.execute(
                    """
                    SELECT COALESCE(MAX(position), 0) + 1
                    FROM WAITLIST
                    WHERE event_id = %s;
                    """,
                    (event_id,),
                )
                pos = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO WAITLIST (user_id, event_id, position, created_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, event_id)
                    DO UPDATE SET position = EXCLUDED.position;
                    """,
                    (user_id, event_id, pos, now),
                )
                return "waitlisted"


# ---------- 5. 取消報名 (含自動遞補) ----------

def cancel_participation(user_id: int, event_id: int) -> bool:
    """
    志工取消報名：
      1. 將 PARTICIPATION.status 改為 'Cancelled'
      2. 從 WAITLIST 中找 position 最小的志工遞補
      3. 遞補成功後，刪掉他的 WAITLIST 記錄，並把其餘 position 往前移一格
    回傳 True = 有這筆報名且流程完成；False = 原本就沒有報名紀錄
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. 鎖住該 event，避免並發遞補混亂
            cur.execute(
                "SELECT event_id FROM TASK_EVENT WHERE event_id = %s FOR UPDATE;",
                (event_id,),
            )
            if cur.fetchone() is None:
                return False

            # 2. 確認是否有報名紀錄
            cur.execute(
                """
                SELECT status
                FROM PARTICIPATION
                WHERE user_id = %s AND event_id = %s;
                """,
                (user_id, event_id),
            )
            row = cur.fetchone()
            if row is None:
                # 原本就沒報名
                return False

            current_status = row[0]
            if current_status == "Cancelled":
                # 已經取消過了，當作成功
                return True

            # 3. 將這位志工標記為 Cancelled
            cur.execute(
                """
                UPDATE PARTICIPATION
                SET status = 'Cancelled'
                WHERE user_id = %s AND event_id = %s;
                """,
                (user_id, event_id),
            )

            # 4. 從 WAITLIST 中找此 event 的第一順位
            cur.execute(
                """
                SELECT user_id
                FROM WAITLIST
                WHERE event_id = %s
                ORDER BY position
                LIMIT 1;
                """,
                (event_id,),
            )
            wl_row = cur.fetchone()
            if wl_row is None:
                # 沒有人在候補，結束
                return True

            next_user_id = wl_row[0]

            # 5. 將候補者加入 / 啟用 PARTICIPATION
            cur.execute(
                """
                INSERT INTO PARTICIPATION (user_id, event_id, join_time, role, status)
                VALUES (%s, %s, NOW(), 'Volunteer', 'Active')
                ON CONFLICT (user_id, event_id)
                DO UPDATE SET
                    status    = 'Active',
                    join_time = EXCLUDED.join_time,
                    role      = 'Volunteer';
                """,
                (next_user_id, event_id),
            )

            # 6. 刪除他的 WAITLIST 記錄
            cur.execute(
                """
                DELETE FROM WAITLIST
                WHERE user_id = %s AND event_id = %s;
                """,
                (next_user_id, event_id),
            )

            # 7. 其餘候補順位往前移一格
            cur.execute(
                """
                UPDATE WAITLIST
                SET position = position - 1
                WHERE event_id = %s
                  AND position > 1;
                """,
                (event_id,),
            )

    return True
