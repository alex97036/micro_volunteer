# backend/admin_cli.py
"""
簡易 Admin CLI（demo 用，未考慮安全性）
功能：
  - 查詢使用者與角色
  - 新增/移除角色（含授權 Organizer、Admin）
  - 管理基礎資料：ORG / VENUE / SKILL
"""
import socket
import json

HOST = "127.0.0.1"
PORT = 5050


def send_request(sock: socket.socket, action: str, params: dict):
    req = {"action": action, "params": params}
    sock.sendall((json.dumps(req) + "\n").encode("utf-8"))
    buf = ""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            print("[ERROR] 與伺服器連線中斷。請確認 server 有在執行。")
            return None
        buf += chunk.decode("utf-8")
        if "\n" in buf:
            line, _ = buf.split("\n", 1)
            line = line.strip()
            break
    resp = json.loads(line)
    if resp.get("status") != "ok":
        msg = resp.get("message", "unknown error")
        print(f"[ERROR] {msg}")
        return None
    return resp.get("data")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print("=== Admin CLI ===")
        user_name = input("請輸入 Admin 帳號: ").strip()
        password = input("請輸入密碼: ").strip()

        login_data = send_request(
            sock, "login", {"user_name": user_name, "password": password}
        )
        if not login_data:
            print("登入失敗")
            return
        roles = login_data.get("roles", [])
        if "Admin" not in roles:
            print("此帳號不是 Admin")
            return
        user_id = login_data["user_id"]

        while True:
            print("\n--- Admin 功能 ---")
            print("1) 列出使用者與角色")
            print("2) 新增角色給使用者")
            print("3) 移除使用者角色")
            print("4) 建立主辦單位 (ORG)")
            print("5) 建立場地 (VENUE)")
            print("6) 建立技能 (SKILL)")
            print("7) 刪除任務 (EVENT)")
            print("8) 刪除場地 (VENUE)")
            print("9) 刪除技能 (SKILL)")
            print("10) 查看熱門搜尋關鍵字")
            print("11) 查看所有任務")
            print("12) 查看任務報名名單")
            print("13) 離開")
            cmd = input("請輸入選項: ").strip()

            if cmd == "1":
                role_filter = input("要查哪一類？(all/Volunteer/Organizer/Admin，Enter=all): ").strip()
                payload = {"user_id": user_id}
                if role_filter and role_filter.lower() != "all":
                    payload["role"] = role_filter
                data = send_request(sock, "admin_list_users", payload)
                if data is not None:
                    print("\n全部使用者：")
                    for u in data:
                        roles = ", ".join(u["roles"])
                        print(f"{u['user_id']} | {u['user_name']} | {u['email']} | 角色: {roles}")

                    def print_by_role(role: str):
                        print(f"\n=== {role} 列表 ===")
                        found = False
                        for u in data:
                            if role in u["roles"]:
                                found = True
                                print(f"{u['user_id']} | {u['user_name']} | {u['email']}")
                        if not found:
                            print("(無)")

                    print_by_role("Volunteer")
                    print_by_role("Organizer")
                    print_by_role("Admin")

            elif cmd == "2":
                target_id = input("目標 user_id: ").strip()
                role = input("角色 (Volunteer/Organizer/Admin): ").strip()
                data = send_request(
                    sock,
                    "admin_add_role",
                    {"user_id": user_id, "target_user_id": target_id, "role": role},
                )
                if data is not None:
                    print("✅ 已新增角色")

            elif cmd == "3":
                target_id = input("目標 user_id: ").strip()
                role = input("要移除的角色: ").strip()
                data = send_request(
                    sock,
                    "admin_remove_role",
                    {"user_id": user_id, "target_user_id": target_id, "role": role},
                )
                if data is not None:
                    print("✅ 已移除角色")

            elif cmd == "4":
                org_name = input("主辦單位名稱: ").strip()
                contact_email = input("聯絡 email: ").strip()
                owner = input("綁定的 organizer user_id (Enter 跳過): ").strip()
                owner_user_id = owner or None
                data = send_request(
                    sock,
                    "create_org",
                    {
                        "user_id": user_id,
                        "org_name": org_name,
                        "contact_email": contact_email,
                        **({"owner_user_id": owner_user_id} if owner_user_id else {}),
                    },
                )
                if data:
                    print(f"✅ ORG 建立成功 org_id={data['org_id']}")

            elif cmd == "5":
                name = input("場地名稱: ").strip()
                address = input("地址: ").strip()
                capacity = input("容量: ").strip()
                data = send_request(
                    sock,
                    "create_venue",
                    {"user_id": user_id, "name": name, "address": address, "capacity": capacity},
                )
                if data:
                    print(f"✅ VENUE 建立成功 venue_id={data['venue_id']}")

            elif cmd == "6":
                skill_name = input("技能名稱: ").strip()
                data = send_request(
                    sock,
                    "admin_create_skill",
                    {"user_id": user_id, "skill_name": skill_name},
                )
                if data:
                    print(f"✅ SKILL 建立成功 skill_id={data['skill_id']}")

            elif cmd == "7":
                event_id = input("event_id: ").strip()
                data = send_request(
                    sock, "admin_delete_event", {"user_id": user_id, "event_id": event_id}
                )
                if data:
                    print("✅ 已刪除任務")

            elif cmd == "8":
                venue_id = input("venue_id: ").strip()
                data = send_request(
                    sock, "admin_delete_venue", {"user_id": user_id, "venue_id": venue_id}
                )
                if data:
                    print("✅ 已刪除場地")

            elif cmd == "9":
                skill_id = input("skill_id: ").strip()
                data = send_request(
                    sock, "admin_delete_skill", {"user_id": user_id, "skill_id": skill_id}
                )
                if data:
                    print("✅ 已刪除技能")

            elif cmd == "10":
                limit = input("想看前幾名？(預設10): ").strip()
                payload = {"user_id": user_id}
                if limit:
                    payload["limit"] = limit
                data = send_request(sock, "admin_top_keywords", payload)
                if data is not None:
                    print("\n=== 熱門關鍵字 ===")
                    for kw, cnt in data:
                        print(f"{kw}: {cnt}")

            elif cmd == "11":
                data = send_request(sock, "admin_list_events", {"user_id": user_id})
                if data is not None:
                    print("\n=== 任務列表 ===")
                    for e in data:
                        print(
                            f"Event {e['event_id']} | {e['title']} | {e['event_date']} "
                            f"{e['start_hour']}:00-{e['end_hour']}:00 | "
                            f"狀態:{e['status']} | 名額:{e['capacity']} | 已報名:{e['active']} | 候補:{e['waitlist']}"
                        )

            elif cmd == "12":
                event_id = input("event_id: ").strip()
                data = send_request(
                    sock, "admin_event_participants", {"user_id": user_id, "event_id": event_id}
                )
                if data is not None:
                    print("\n=== 報名名單 ===")
                    for p in data:
                        print(
                            f"{p['user_id']} | {p['user_name']} | {p['email']} | "
                            f"{p['phone']} | {p['role']} | {p['status']} | {p['join_time']}"
                        )

            elif cmd == "13":
                print("Bye")
                break
            else:
                print("無效選項")


if __name__ == "__main__":
    main()
