# backend/server.py
import socket
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import threading
from db import get_conn
from analytics import log_search, top_keywords
from volunteer import (
    register_user,
    search_tasks,
    join_task,
    cancel_participation,
    get_user_history,
    get_user_roles,
    user_has_role,
    list_users_with_roles,
    add_role,
    remove_role,
    create_skill,
    mark_finished_events,
    update_user_profile,
    get_event_participants,
    get_venue_bookings,
    is_venue_available,
    get_user_active_participation,
)
from organizer import (
    create_org,
    create_venue,
    create_event,
    set_event_periods,
    set_required_skills,
    list_my_events,
    list_venues,
    list_skills,
    get_or_create_default_org,
    list_all_events_with_counts,
)


HOST = "127.0.0.1"
PORT = 5050
REGISTRATION_ROLES = {"Volunteer", "Organizer"}


def serialize(obj: Any) -> Any:
    """把 date/datetime 轉成字串，方便丟回給 client"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize(v) for v in obj]
    return obj


def handle_request(req: Dict) -> Dict:
    """根據 action 處理一個請求，回傳 dict"""
    action = req.get("action")
    params = req.get("params", {})

    # 每次請求先把已過期活動標記 Finished
    try:
        mark_finished_events()
    except Exception:
        # 不影響主流程，忽略
        pass

    def require_role(user_id: int, role: str) -> Optional[Dict]:
        if not user_has_role(user_id, role):
            return {"status": "error", "message": f"需具備 {role} 身分才能執行。"}
        return None

    try:
        if action == "register_user":
            user_name = params["user_name"]
            email = params["email"]
            phone = int(params["phone"])
            password = params["password"]
            role = params.get("role", "Volunteer")
            role = role.strip().lower().capitalize()
            if role not in REGISTRATION_ROLES:
                return {
                    "status": "error",
                    "message": "註冊角色僅支援 Volunteer 或 Organizer。",
                }
            user_id = register_user(user_name, email, phone, password, role)
            # 如果是 Organizer，自動建立一個同名 ORG 並綁定
            if role == "Organizer":
                create_org(f"{user_name} Org", email or f"{user_name}@example.org", user_id)
            return {"status": "ok", "data": {"user_id": user_id, "roles": [role]}}

        elif action == "login":
            user_name = params["user_name"]
            password = params["password"]
            login_result = login_user(user_name, password)
            if login_result is None:
                # 帳號或密碼錯誤
                return {
                    "status": "error",
                    "message": "帳號或密碼錯誤，請重新確認。",
                }
            user_id, roles = login_result
            if not roles:
                return {
                    "status": "error",
                    "message": "此帳號尚未被指派任何角色，請聯絡管理員。",
                }
            return {
                "status": "ok",
                "data": {"user_id": user_id, "user_name": user_name, "roles": roles},
            }
        # ---------- Organizer 功能 ----------
        elif action == "create_venue":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Organizer")
            if err:
                return err
            name = params["name"]
            address = params["address"]
            capacity = int(params["capacity"])
            venue_id = create_venue(name, address, capacity)
            return {"status": "ok", "data": {"venue_id": venue_id}}

        elif action == "create_org":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Organizer")
            if err:
                return err
            org_name = params["org_name"]
            contact_email = params["contact_email"]
            owner_user_id = int(params.get("owner_user_id", user_id))
            org_id = create_org(org_name, contact_email, owner_user_id)
            return {"status": "ok", "data": {"org_id": org_id}}

        elif action == "create_event":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Organizer")
            if err:
                return err
            owner_id = user_id  # 以自己為 owner
            org_id = params.get("org_id")
            if org_id is not None:
                org_id = int(org_id)
            else:
                org_id = get_or_create_default_org(user_id)
            venue_id = int(params["venue_id"])
            event_date = date.fromisoformat(params["event_date"])
            start_hour = int(params["start_hour"])
            end_hour = int(params["end_hour"])
            capacity = int(params["capacity"])
            # 場地是否可用
            if not is_venue_available(venue_id, event_date, start_hour, end_hour):
                return {"status": "error", "message": "該場地該時段已被預約，請換時間"}
            title = params.get("title", "")
            description = params.get("description", "")
            status = params.get("status", "Planned")
            event_id = create_event(
                owner_id,
                org_id,
                venue_id,
                event_date,
                start_hour,
                end_hour,
                capacity,
                title,
                description,
                status,
            )
            return {"status": "ok", "data": {"event_id": event_id}}

        elif action == "set_event_periods":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Organizer")
            if err:
                return err
            event_id = int(params["event_id"])
            if "start_hour" in params and "end_hour" in params:
                start_hour = int(params["start_hour"])
                end_hour = int(params["end_hour"])
                hours = list(range(start_hour, end_hour))
            else:
                hours = [int(h) for h in params.get("hours", [])]
            set_event_periods(event_id, hours)
            return {"status": "ok", "data": True}

        elif action == "set_required_skills":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Organizer")
            if err:
                return err
            event_id = int(params["event_id"])
            skill_weights = params.get("skill_weights", {})
            set_required_skills(event_id, skill_weights)
            return {"status": "ok", "data": True}

        elif action == "list_my_events":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Organizer")
            if err:
                return err
            events = list_my_events(user_id)
            return {"status": "ok", "data": serialize(events)}

        elif action == "list_venues":
            venues = list_venues()
            return {"status": "ok", "data": venues}

        elif action == "list_skills":
            skills = list_skills()
            return {"status": "ok", "data": skills}

        elif action == "get_event_participants":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Organizer")
            if err:
                return err
            event_id = int(params["event_id"])
            # 確認是自己的任務
            events = list_my_events(user_id)
            if not any(e["event_id"] == event_id for e in events):
                return {"status": "error", "message": "僅能查看自己建立的任務"}
            participants = get_event_participants(event_id)
            return {"status": "ok", "data": serialize(participants)}

        elif action == "check_venue_availability":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Organizer")
            if err:
                return err
            venue_id = int(params["venue_id"])
            event_date = date.fromisoformat(params["event_date"])
            start_hour = int(params["start_hour"])
            end_hour = int(params["end_hour"])
            available = is_venue_available(venue_id, event_date, start_hour, end_hour)
            conflicts = get_venue_bookings(venue_id, event_date) if not available else []
            return {"status": "ok", "data": {"available": available, "conflicts": conflicts}}

        elif action == "list_venue_bookings":
            venue_id = int(params["venue_id"])
            event_date = date.fromisoformat(params["event_date"])
            bookings = get_venue_bookings(venue_id, event_date)
            return {"status": "ok", "data": serialize(bookings)}

        # ---------- Admin 功能（簡化） ----------
        elif action == "admin_list_users":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Admin")
            if err:
                return err
            role_filter = params.get("role")
            users = list_users_with_roles()
            if role_filter:
                role_std = role_filter.strip().lower().capitalize()
                users = [u for u in users if role_std in u.get("roles", [])]
            return {"status": "ok", "data": users}

        elif action == "admin_add_role":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Admin")
            if err:
                return err
            target_user_id = int(params["target_user_id"])
            role = params["role"]
            add_role(target_user_id, role)
            return {"status": "ok", "data": True}

        elif action == "admin_remove_role":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Admin")
            if err:
                return err
            target_user_id = int(params["target_user_id"])
            role = params["role"]
            remove_role(target_user_id, role)
            return {"status": "ok", "data": True}

        elif action == "admin_create_skill":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Admin")
            if err:
                return err
            skill_name = params["skill_name"]
            skill_id = create_skill(skill_name)
            return {"status": "ok", "data": {"skill_id": skill_id}}

        elif action == "admin_delete_event":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Admin")
            if err:
                return err
            event_id = int(params["event_id"])
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM TASK_EVENT WHERE event_id = %s;", (event_id,))
            return {"status": "ok", "data": True}

        elif action == "admin_delete_venue":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Admin")
            if err:
                return err
            venue_id = int(params["venue_id"])
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM VENUE WHERE venue_id = %s;", (venue_id,))
            return {"status": "ok", "data": True}

        elif action == "admin_delete_skill":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Admin")
            if err:
                return err
            skill_id = int(params["skill_id"])
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM SKILL WHERE skill_id = %s;", (skill_id,))
            return {"status": "ok", "data": True}

        elif action == "admin_top_keywords":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Admin")
            if err:
                return err
            limit = int(params.get("limit", 10))
            kws = top_keywords(limit)
            return {"status": "ok", "data": kws}

        elif action == "admin_list_events":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Admin")
            if err:
                return err
            events = list_all_events_with_counts()
            return {"status": "ok", "data": serialize(events)}

        elif action == "admin_event_participants":
            user_id = int(params["user_id"])
            err = require_role(user_id, "Admin")
            if err:
                return err
            event_id = int(params["event_id"])
            participants = get_event_participants(event_id)
            return {"status": "ok", "data": serialize(participants)}

        elif action == "update_profile":
            user_id = int(params["user_id"])
            update_user_profile(
                user_id,
                user_name=params.get("user_name"),
                email=params.get("email"),
                phone=int(params["phone"]) if params.get("phone") else None,
                password=params.get("password"),
            )
            return {"status": "ok", "data": True}

        elif action == "search_tasks":
            # 文字轉成 date，如果是空字串就 None
            event_date_str = params.get("event_date")
            if event_date_str:
                event_date = date.fromisoformat(event_date_str)
            else:
                event_date = None

            location_keyword = params.get("location_keyword") or None
            skill_keyword = params.get("skill_keyword") or None
            title_keyword = params.get("title_keyword") or params.get("keyword") or None
            only_available = bool(params.get("only_available", True))
            include_finished = bool(params.get("include_finished", False))
            only_finished = bool(params.get("only_finished", False))
            future_only = bool(params.get("future_only", False))
            past_only = bool(params.get("past_only", False))
            user_id = int(params.get("user_id", 0)) if params.get("user_id") is not None else None

            tasks = search_tasks(
                event_date=event_date,
                location_keyword=location_keyword,
                skill_keyword=skill_keyword,
                title_keyword=title_keyword,
                only_available=only_available,
                include_finished=include_finished,
                only_finished=only_finished,
                future_only=future_only,
                past_only=past_only,
            )
            try:
                log_search(
                    user_id or 0,
                    title_keyword or "",
                    {
                        "event_date": event_date_str or "",
                        "location": location_keyword or "",
                        "skill": skill_keyword or "",
                        "only_available": only_available,
                        "history": only_finished or past_only,
                    },
                    is_history=only_finished or past_only,
                )
            except Exception:
                pass
            return {"status": "ok", "data": serialize(tasks)}

        elif action == "join_task":
            user_id = int(params["user_id"])
            if not user_has_role(user_id, "Volunteer"):
                return {
                    "status": "error",
                    "message": "需具備 Volunteer 身分才能報名任務。",
                }
            event_id = int(params["event_id"])
            result = join_task(user_id, event_id)
            # result 可能是 "joined" 或 "waitlisted"
            return {"status": "ok", "data": {"result": result}}

        elif action == "cancel_participation":
            user_id = int(params["user_id"])
            if not user_has_role(user_id, "Volunteer"):
                return {
                    "status": "error",
                    "message": "需具備 Volunteer 身分才能取消報名。",
                }
            event_id = int(params["event_id"])
            success = cancel_participation(user_id, event_id)
            return {"status": "ok", "data": {"success": success}}

        elif action == "get_user_history":
            user_id = int(params["user_id"])
            if not user_has_role(user_id, "Volunteer"):
                return {
                    "status": "error",
                    "message": "需具備 Volunteer 身分才能查看參與紀錄。",
                }
            history = get_user_history(user_id)
            return {"status": "ok", "data": serialize(history)}

        elif action == "get_user_active_participation":
            user_id = int(params["user_id"])
            if not user_has_role(user_id, "Volunteer"):
                return {
                    "status": "error",
                    "message": "需具備 Volunteer 身分才能查看報名列表。",
                }
            data = get_user_active_participation(user_id)
            return {"status": "ok", "data": serialize(data)}

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    except Exception as e:
        # 任何例外丟回去
        return {"status": "error", "message": str(e)}


def handle_client(conn: socket.socket, addr):
    print(f"[SERVER] Connected by {addr}")
    with conn:
        buf = ""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk.decode("utf-8")
            # 以換行為一筆 request
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    req = json.loads(line)
                except json.JSONDecodeError:
                    resp = {"status": "error", "message": "Invalid JSON"}
                else:
                    resp = handle_request(req)

                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
    print(f"[SERVER] Connection closed {addr}")


def main():
    ensure_admin_account()
    print(f"[SERVER] Listening on {HOST}:{PORT} ...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(50)  # 提高 backlog，允許多個連線
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()

def login_user(user_name: str, password: str):
    """
    用 user_name + password 登入：
    回傳 (user_id, roles)；找不到就回傳 None
    """
    sql = 'SELECT user_id FROM "USER" WHERE user_name = %s AND password = %s'
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_name, password))
            row = cur.fetchone()
    if row:
        user_id = row[0]
        roles = get_user_roles(user_id)
        return user_id, roles
    return None


def ensure_admin_account():
    """
    確保存在預設的 Admin 帳號（user_name=alex, password=1234）
    demo 用，未考慮安全性
    """
    default_user = "alex"
    default_pass = "1234"
    default_email = "alex@example.org"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT user_id FROM "USER" WHERE user_name = %s;',
                (default_user,),
            )
            row = cur.fetchone()
            if row:
                user_id = row[0]
            else:
                cur.execute(
                    """
                    INSERT INTO "USER" (user_name, email, phone, password)
                    VALUES (%s, %s, %s, %s)
                    RETURNING user_id;
                    """,
                    (default_user, default_email, 99999999, default_pass),
                )
                user_id = cur.fetchone()[0]

            # 確保有 Admin 角色
            for role in ("Admin", "Organizer", "Volunteer"):
                cur.execute(
                    """
                    INSERT INTO USER_ROLE (user_id, role)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, role) DO NOTHING;
                    """,
                    (user_id, role),
                )

if __name__ == "__main__":
    main()
