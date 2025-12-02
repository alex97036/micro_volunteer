# backend/volunteer_demo.py
from datetime import date,timedelta
from volunteer import search_tasks, get_user_history, cancel_participation
from volunteer import (
    register_user,
    create_skill,
    set_user_skill,
    search_tasks,
    join_task,
    cancel_participation,
)

def main():
    print("=== Volunteer demo ===")
    '''
    # 1. 建一個 user
    user_id = register_user("alex", "alex@example.com", 12345678, "pw123")
    print("new user_id =", user_id)

    # 2. 建一個 skill 並設定等級
    skill_id = create_skill("Python")
    set_user_skill(user_id, skill_id, level=4)
    print(f"user {user_id} skill {skill_id} set to level 4")

    # 3. 查詢目前任務 (這裡先只看列表，之後你可以先手動用 SQL 建一個 TASK_EVENT)
    tasks = search_tasks()
    print("tasks:", tasks)

    # 假設有一個 event_id = 1 的任務，試著報名
    event_id = 1
    try:
        result = join_task(user_id, event_id)
        print(f"join_task result = {result}")
    except Exception as e:
        print("join_task error:", e)

    # 4. 取消報名（測試自動遞補）
    try:
        cancel_participation(user_id, event_id)
        print("cancel_participation done")
    except Exception as e:
        print("cancel error:", e)
    '''
    print("new")
    # 1. 搜尋明天在台南的淨灘任務
    tasks = search_tasks(
        event_date=date.today()+ timedelta(days=1),
        location_keyword="台南",        # 或 "Tainan"
        skill_keyword="Beach",         # 想要需要淨灘技能的
        only_available=True,
    )
    print("tasks =", tasks)

    # 2. 看 user 1 的歷史紀錄
    print(get_user_history(1))
    print(get_user_history(4))  # 可能是 vol_anna
    print(get_user_history(5))
    print(get_user_history(6))
    print(get_user_history(7))

    # 3. 取消報名某個 event，並觸發候補遞補
    cancel_participation(user_id=1, event_id=1)

    

if __name__ == "__main__":
    main()