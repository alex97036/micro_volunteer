# backend/client.py
import socket
import json
from datetime import date

HOST = "127.0.0.1"
PORT = 5050


def send_request(sock: socket.socket, action: str, params: dict):
    req = {"action": action, "params": params}
    sock.sendall((json.dumps(req) + "\n").encode("utf-8"))
    # 單行 response，累積到換行（避免 4096 bytes 剪斷 JSON）
    buf = ""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            print("[ERROR] 與伺服器連線中斷")
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


def show_tasks(tasks):
    if not tasks:
        print("目前沒有符合條件的任務。")
        return
    print("\n=== 任務列表 ===")
    for t in tasks:
        time_str = ""
        if "start_hour" in t and "end_hour" in t:
            time_str = f"{t['start_hour']}:00-{t['end_hour']}:00 "
        print(
            f"Event {t['event_id']}: {t['title']}  "
            f"日期: {t['date']} {time_str} 地點: {t['venue']}  "
            f"名額: {t['active_volunteers']}/{t['capacity']}  "
            f"剩餘: {t['slots_left']}"
        )
    print("==============\n")


def show_history(history):
    if not history:
        print("目前沒有參加紀錄。")
        return
    print("\n=== 歷史紀錄 ===")
    for h in history:
        print(
            f"[{h['date']}] {h['title']} @ {h['venue']} "
            f"角色: {h['role']} 狀態: {h['status']} "
            f"(加入時間: {h['join_time']})"
        )
    print("==============\n")


def organizer_menu(sock, user_id):
    while True:
        print("\n=== Organizer 主選單 ===")
        print("1) 建立場地")
        print("2) 建立主辦單位")
        print("3) 建立任務")
        print("4) 設定任務時間")
        print("5) 設定任務所需技能")
        print("6) 查看我的任務列表")
        print("7) 查看任務報名名單")
        print("8) 查看場地列表")
        print("9) 查看技能列表")
        print("10) 檢查場地時段可用性")
        print("11) 返回")
        cmd = input("請輸入選項: ").strip()

        if cmd == "1":
            name = input("場地名稱: ").strip()
            address = input("地址: ").strip()
            capacity = input("容量: ").strip()
            data = send_request(
                sock,
                "create_venue",
                {
                    "user_id": user_id,
                    "name": name,
                    "address": address,
                    "capacity": capacity,
                },
            )
            if data:
                print(f"✅ 建立成功，venue_id = {data['venue_id']}")

        elif cmd == "2":
            org_name = input("主辦單位名稱: ").strip()
            contact_email = input("聯絡 email: ").strip()
            data = send_request(
                sock,
                "create_org",
                {
                    "user_id": user_id,
                    "org_name": org_name,
                    "contact_email": contact_email,
                },
            )
            if data:
                print(f"✅ 建立成功，org_id = {data['org_id']}")

        elif cmd == "3":
            venue_id = input("venue_id: ").strip()
            start_hour = input("開始時間(0-23): ").strip()
            end_hour = input("結束時間(1-23，最多+3小時): ").strip()
            event_date = input("日期 (YYYY-MM-DD): ").strip()
            capacity = input("名額上限: ").strip()
            title = input("標題: ").strip()
            description = input("描述: ").strip()
            data = send_request(
                sock,
                "create_event",
                {
                    "user_id": user_id,
                    "venue_id": venue_id,
                    "start_hour": start_hour,
                    "end_hour": end_hour,
                    "event_date": event_date,
                    "capacity": capacity,
                    "title": title,
                    "description": description,
                },
            )
            if data:
                print(f"✅ 任務建立成功，event_id = {data['event_id']}")

        elif cmd == "4":
            event_id = input("event_id: ").strip()
            start_hour = input("開始時間(0-23): ").strip()
            end_hour = input("結束時間(1-23): ").strip()
            data = send_request(
                sock,
                "set_event_periods",
                {
                    "user_id": user_id,
                    "event_id": event_id,
                    "start_hour": start_hour,
                    "end_hour": end_hour,
                },
            )
            if data is not None:
                print("✅ 已設定時間")

        elif cmd == "5":
            event_id = input("event_id: ").strip()
            print("輸入技能與權重，格式: SkillName:Weight，多個以逗號分隔，如 First Aid:2,Logistics:1")
            sw_str = input("技能清單: ").strip()
            skill_weights = {}
            if sw_str:
                for pair in sw_str.split(","):
                    if ":" in pair:
                        name, w = pair.split(":", 1)
                        skill_weights[name.strip()] = int(w.strip())
            data = send_request(
                sock,
                "set_required_skills",
                {
                    "user_id": user_id,
                    "event_id": event_id,
                    "skill_weights": skill_weights,
                },
            )
            if data is not None:
                print("✅ 已設定所需技能")

        elif cmd == "6":
            data = send_request(sock, "list_my_events", {"user_id": user_id})
            if data is not None:
                print("\n=== 我的任務列表 ===")
                for e in data:
                    print(
                        f"Event {e['event_id']} | {e['title']} | 日期: {e['event_date']} "
                        f"{e['start_hour']}:00-{e['end_hour']}:00 | "
                        f"狀態: {e['status']} | 名額: {e['capacity']} | "
                        f"已報名: {e.get('active',0)} / 候補: {e.get('waitlist',0)}"
                    )
                print("==============\n")

        elif cmd == "7":
            event_id = input("event_id: ").strip()
            data = send_request(
                sock,
                "get_event_participants",
                {"user_id": user_id, "event_id": event_id},
            )
            if data is not None:
                print("\n=== 報名名單 ===")
                for p in data:
                    print(
                        f"{p['user_id']} | {p['user_name']} | {p['email']} | "
                        f"{p['phone']} | {p['role']} | {p['status']} | {p['join_time']}"
                    )
                print("==============\n")

        elif cmd == "8":
            data = send_request(sock, "list_venues", {})
            if data is not None:
                print("\n=== 場地列表 ===")
                for v in data:
                    print(
                        f"Venue {v['venue_id']} | {v['name']} | {v['address']} | 容量 {v['capacity']}"
                    )
                print("==============\n")

        elif cmd == "9":
            data = send_request(sock, "list_skills", {})
            if data is not None:
                print("\n=== 技能列表 ===")
                for s in data:
                    print(f"{s['skill_id']}: {s['skill_name']}")
                print("==============\n")

        elif cmd == "10":
            venue_id = input("venue_id: ").strip()
            event_date = input("日期 (YYYY-MM-DD): ").strip()
            start_hour = input("開始時間(0-23): ").strip()
            end_hour = input("結束時間(1-23): ").strip()
            if not event_date or not start_hour or not end_hour:
                print("日期與時間欄位不可空白。")
                continue
            # 基本格式檢查
            try:
                date.fromisoformat(event_date)
            except ValueError:
                print("日期格式錯誤，請用 YYYY-MM-DD")
                continue
            data = send_request(
                sock,
                "check_venue_availability",
                {
                    "user_id": user_id,
                    "venue_id": venue_id,
                    "event_date": event_date,
                    "start_hour": start_hour,
                    "end_hour": end_hour,
                },
            )
            if data is not None:
                if data["available"]:
                    print("✅ 可預約")
                else:
                    print("⚠ 已被預約，衝突清單：")
                    for c in data["conflicts"]:
                        print(
                            f"Event {c['event_id']} | {c['title']} | {c['start_hour']}:00-{c['end_hour']}:00 | 狀態:{c['status']}"
                        )

        elif cmd == "11":
            break
        else:
            print("無效的選項，請重新輸入。")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print("已連線到伺服器。")

        # 先決定 user 身分
        print("=== 志工系統登入 ===")
        print("1) 使用既有帳號登入")
        print("2) 註冊新帳號")
        choice = input("請選擇 (1/2): ").strip()

        user_id = None
        roles = []

        if choice == "1":
            print("=== 帳號登入 ===")
            user_name = input("帳號（user_name）: ").strip()
            password = input("密碼: ").strip()
            data = send_request(
                sock,
                "login",
                {"user_name": user_name, "password": password},
            )
            if not data:
                # send_request 已經印過 [ERROR] 訊息
                print("登入失敗，程式結束。")
                return
            user_id = data["user_id"]
            roles = data.get("roles", [])
            print(f"登入成功！user_id = {user_id}，角色：{', '.join(roles)}")
        else:
            print("=== 註冊新帳號 ===")
            user_name = input("姓名: ").strip()
            email = input("Email: ").strip()
            phone = input("電話(數字即可): ").strip()
            password = input("密碼: ").strip()
            print("角色（預設 Volunteer）：")
            print("1) Volunteer  2) Organizer  （Admin 請由系統建立）")
            role_choice = input("請選擇 (1/2，Enter=1): ").strip()
            if role_choice == "2":
                role = "Organizer"
            else:
                role = "Volunteer"
            data = send_request(
                sock,
                "register_user",
                {
                    "user_name": user_name,
                    "email": email,
                    "phone": phone,
                    "password": password,
                    "role": role,
                },
            )
            if not data:
                print("註冊失敗，結束。")
                return
            user_id = data["user_id"]
            roles = data.get("roles", [role])
            print(f"註冊成功，你的 user_id = {user_id}，角色：{', '.join(roles)}")

        is_volunteer = "Volunteer" in roles
        is_organizer = "Organizer" in roles
        if not is_volunteer and not is_organizer:
            print("目前 CLI 只支援 Volunteer/Organizer 功能，請確認角色。")
            return

        # 主選單
        while True:
            print("\n=== 主選單 ===")
            opts = []
            if is_volunteer:
                opts.extend(
                    [
                        "1) 志工：搜尋任務",
                        "2) 志工：搜尋歷史任務（已結束）",
                        "3) 志工：報名任務",
                        "4) 志工：取消報名",
                        "5) 志工：查看歷史紀錄",
                        "6) 志工：查看已報名的任務",
                        "7) 志工：更新個人資料",
                    ]
                )
            next_idx = 8 if is_volunteer else 1
            org_option = None
            if is_organizer:
                org_option = next_idx
                opts.append(f"{next_idx}) Organizer 功能")
                next_idx += 1
            opts.append(f"{next_idx}) 離開")
            for line in opts:
                print(line)
            cmd = input("請輸入選項: ").strip()

            if is_volunteer and cmd == "1":
                # 搜尋條件
                date_str = input("日期 (YYYY-MM-DD，或直接 Enter 略過): ").strip()
                if not date_str:
                    event_date = ""
                else:
                    # 粗略檢查格式
                    try:
                        date.fromisoformat(date_str)
                    except ValueError:
                        print("日期格式錯誤，將忽略日期條件。")
                        event_date = ""
                    else:
                        event_date = date_str

                loc = input("地點關鍵字 (Enter 略過): ").strip()
                title_kw = input("任務名稱關鍵字 (Enter 略過): ").strip()
                skill = input("技能關鍵字 (Enter 略過): ").strip()
                only_avail_str = input("只顯示尚未額滿的任務？(Y/n): ").strip().lower()
                only_avail = not (only_avail_str == "n")

                data = send_request(
                    sock,
                    "search_tasks",
                    {
                        "event_date": event_date,
                        "location_keyword": loc,
                        "title_keyword": title_kw,
                        "skill_keyword": skill,
                        "only_available": only_avail,
                        "include_finished": False,
                        "only_finished": False,
                        "future_only": True,
                        "past_only": False,
                        "user_id": user_id,
                    },
                )
                if data is not None:
                    show_tasks(data)

            elif is_volunteer and cmd == "2":
                # 歷史任務（只看已結束）
                date_str = input("日期 (YYYY-MM-DD，或直接 Enter 略過): ").strip()
                if not date_str:
                    event_date = ""
                else:
                    try:
                        date.fromisoformat(date_str)
                    except ValueError:
                        print("日期格式錯誤，將忽略日期條件。")
                        event_date = ""
                    else:
                        event_date = date_str
                loc = input("地點關鍵字 (Enter 略過): ").strip()
                title_kw = input("任務名稱關鍵字 (Enter 略過): ").strip()
                skill = input("技能關鍵字 (Enter 略過): ").strip()
                data = send_request(
                    sock,
                    "search_tasks",
                    {
                        "event_date": event_date,
                        "location_keyword": loc,
                        "title_keyword": title_kw,
                        "skill_keyword": skill,
                        "only_available": False,
                        "include_finished": True,
                        "only_finished": True,
                        "future_only": False,
                        "past_only": True,
                        "user_id": user_id,
                    },
                )
                if data is not None:
                    show_tasks(data)

            elif is_volunteer and cmd == "3":
                event_id = input("請輸入要報名的 event_id: ").strip()
                if not event_id:
                    continue
                data = send_request(
                    sock,
                    "join_task",
                    {"user_id": user_id, "event_id": event_id},
                )
                if data is not None:
                    result = data["result"]
                    if result == "joined":
                        print("✅ 報名成功！")
                    elif result == "waitlisted":
                        print("⚠ 名額已滿，你已被加入候補。")
                    else:
                        print("未知結果：", result)

            elif is_volunteer and cmd == "4":
                event_id = input("請輸入要取消的 event_id: ").strip()
                if not event_id:
                    continue
                data = send_request(
                    sock,
                    "cancel_participation",
                    {"user_id": user_id, "event_id": event_id},
                )
                if data is not None:
                    if data["success"]:
                        print("✅ 已取消報名（如果有候補會自動遞補）。")
                    else:
                        print("⚠ 查無報名紀錄。")

            elif is_volunteer and cmd == "5":
                data = send_request(sock, "get_user_history", {"user_id": user_id})
                if data is not None:
                    show_history(data)

            elif is_volunteer and cmd == "6":
                data = send_request(sock, "get_user_active_participation", {"user_id": user_id})
                if data is not None:
                    print("\n=== 已報名任務 ===")
                    if not data:
                        print("目前沒有報名任何任務。")
                    for h in data:
                        print(
                            f"[{h['date']} {h['start_hour']}:00-{h['end_hour']}:00] {h['title']} @ {h['venue']} "
                            f"(加入時間: {h['join_time']})"
                        )
                    print("==============\n")

            elif is_volunteer and cmd == "7":
                print("留下要修改的欄位，若不改請直接 Enter")
                new_name = input("新姓名: ").strip()
                new_email = input("新 Email: ").strip()
                new_phone = input("新電話(數字): ").strip()
                new_pw = input("新密碼: ").strip()
                payload = {"user_id": user_id}
                if new_name:
                    payload["user_name"] = new_name
                if new_email:
                    payload["email"] = new_email
                if new_phone:
                    payload["phone"] = new_phone
                if new_pw:
                    payload["password"] = new_pw
                data = send_request(sock, "update_profile", payload)
                if data is not None:
                    print("✅ 已更新個人資料")

            elif is_organizer and org_option and cmd == str(org_option):
                organizer_menu(sock, user_id)

            elif cmd == str(next_idx):
                print("再見～")
                break

            else:
                print("無效的選項，請重新輸入。")

                
if __name__ == "__main__":   
    main()                   
