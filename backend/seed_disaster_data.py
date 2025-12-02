# backend/seed_disaster_data.py
from datetime import date, timedelta
import random

from db import get_conn
from volunteer import (
    create_skill,
    set_user_skill,
    join_task,
)
from organizer import (
    create_org,
    create_venue,
    create_event,
    set_event_periods,
    set_required_skills,
)
from analytics import seed_dummy_logs


def get_or_create_user_with_role(
    user_name: str, email: str, phone: int, password: str, role: str
) -> int:
    """若帳號存在就回傳 user_id，否則建立並加上角色"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT user_id FROM "USER" WHERE user_name = %s;', (user_name,))
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
                    (user_name, email, phone, password),
                )
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


def seed_bulk_data(
    volunteers: int = 10000,
    extra_orgs: int = 20,
    extra_venues: int = 30,
    skills: int = 12,
    events: int = 100,
):
    """
    建大量測試資料：
      - volunteers: 志工數量
      - extra_orgs: 額外主辦單位/Organizer
      - extra_venues: 額外場地
      - skills: 技能數量
      - events: 任務數量
    """
    today = date.today()

    # 1) 技能
    skill_ids = []
    for i in range(skills):
        skill_ids.append(create_skill(f"Skill_{i+1}"))

    # 2) 額外 Organizer + ORG
    organizer_ids = []
    org_ids = []
    for i in range(extra_orgs):
        uname = f"org_extra_{i+1}"
        email = f"{uname}@example.org"
        uid = get_or_create_user_with_role(uname, email, 80000000 + i, "pw", "Organizer")
        organizer_ids.append(uid)
        org_id = create_org(f"Extra Org {i+1}", email, uid)
        org_ids.append(org_id)

    # 3) 額外場地
    venue_ids = []
    for i in range(extra_venues):
        capacity = random.randint(10, 50)
        venue_ids.append(
            create_venue(f"Extra Venue {i+1}", f"Address {i+1}", capacity)
        )

    # 4) 志工
    volunteer_ids = []
    for i in range(volunteers):
        uname = f"vol_{i+1:05d}"
        email = f"{uname}@example.org"
        phone = 70000000 + i
        uid = get_or_create_user_with_role(uname, email, phone, "pw", "Volunteer")
        volunteer_ids.append(uid)
        # 隨機賦予 1~3 個技能
        for skill_id in random.sample(skill_ids, k=random.randint(1, min(3, len(skill_ids)))):
            set_user_skill(uid, skill_id, level=random.randint(1, 5))

    # 5) 任務
    event_ids = []
    for i in range(events):
        owner_id = random.choice(organizer_ids)
        org_id = org_ids[organizer_ids.index(owner_id)] if owner_id in organizer_ids else random.choice(org_ids)
        venue_id = random.choice(venue_ids)
        day_offset = random.randint(-10, 15)
        ev_date = today + timedelta(days=day_offset)
        start_hour = random.randint(8, 18)
        duration = random.randint(1, 3)
        end_hour = min(start_hour + duration, 23)
        capacity = random.randint(3, 12)
        title = f"任務 {i+1}"
        description = f"自動產生的任務 {i+1}，測試用"
        event_id = create_event(
            owner_id=owner_id,
            org_id=org_id,
            venue_id=venue_id,
            event_date=ev_date,
            start_hour=start_hour,
            end_hour=end_hour,
            capacity=capacity,
            title=title,
            description=description,
            status="Planned",
        )
        set_event_periods(event_id, list(range(start_hour, end_hour)))
        set_required_skills(
            event_id,
            {
                # 隨機選 2 個技能
                f"Skill_{sid}": random.randint(1, 3)
                for sid in random.sample(range(1, skills + 1), k=2)
            },
        )
        event_ids.append(event_id)

    # 6) 隨機報名（3~5 人），可能滿或候補
    for eid in event_ids:
        joiners = random.sample(volunteer_ids, k=random.randint(3, 5))
        for uid in joiners:
            try:
                join_task(uid, eid)
            except Exception:
                pass

    print(
        f"✅ Bulk data seeded: {len(volunteer_ids)} volunteers, "
        f"{len(org_ids)} orgs, {len(venue_ids)} venues, {len(event_ids)} events."
    )


def seed_disaster_data():
    # -------- 1. 建立組織（ORG） --------
    org_tdrc = create_org("Taiwan Disaster Relief Center", "tdrc@example.org")
    org_coast = create_org("Coastal Cleanup Alliance", "coast@example.org")
    org_food = create_org("Community Food Bank", "foodbank@example.org")

    # -------- 2. 建立場地（VENUE） --------
    venue_warehouse = create_venue("台中物資倉庫", "Taichung Warehouse A", 30)
    venue_beach = create_venue("台南海灘", "Tainan Coastal Park", 50)
    venue_shelter = create_venue("高雄臨時收容所", "Kaohsiung Gym Shelter", 80)

    # -------- 3. 建立技能（SKILL） --------
    skill_first_aid = create_skill("First Aid")
    skill_logistics = create_skill("Logistics")
    skill_debris = create_skill("Debris Removal")
    skill_beach = create_skill("Beach Cleaning")
    skill_food = create_skill("Food Distribution")
    skill_crowd = create_skill("Crowd Management")

    # -------- 4. 建立主辦者使用者（Organizer） --------
    org_tc_id = get_or_create_user_with_role(
        "org_taichung", "org_tc@example.org", 11111111, "pw", "Organizer"
    )
    org_tn_id = get_or_create_user_with_role(
        "org_tainan", "org_tn@example.org", 22222222, "pw", "Organizer"
    )
    org_kh_id = get_or_create_user_with_role(
        "org_kaohsiung", "org_kh@example.org", 33333333, "pw", "Organizer"
    )

    # 綁定 organizer 與 org（各自一個）
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ORGANIZER_ORG (user_id, org_id)
                VALUES
                  (%s, %s),
                  (%s, %s),
                  (%s, %s)
                ON CONFLICT (user_id, org_id) DO NOTHING;
                """,
                (org_tc_id, org_tdrc, org_tn_id, org_coast, org_kh_id, org_food),
            )

    # -------- 5. 建立志工使用者（Volunteer）＋技能 --------
    vol_anna = get_or_create_user_with_role("vol_anna", "anna@example.org", 44444444, "pw", "Volunteer")
    vol_bob = get_or_create_user_with_role("vol_bob", "bob@example.org", 55555555, "pw", "Volunteer")
    vol_chris = get_or_create_user_with_role("vol_chris", "chris@example.org", 66666666, "pw", "Volunteer")
    vol_dora = get_or_create_user_with_role("vol_dora", "dora@example.org", 77777777, "pw", "Volunteer")

    with get_conn() as conn:
        with conn.cursor() as cur:
            for uid in (vol_anna, vol_bob, vol_chris, vol_dora):
                cur.execute(
                    """
                    INSERT INTO USER_ROLE (user_id, role)
                    VALUES (%s, 'Volunteer')
                    ON CONFLICT (user_id, role) DO NOTHING;
                    """,
                    (uid,),
                )

    # 設定志工技能
    set_user_skill(vol_anna, skill_first_aid, 5)
    set_user_skill(vol_anna, skill_crowd, 4)

    set_user_skill(vol_bob, skill_logistics, 5)
    set_user_skill(vol_bob, skill_debris, 4)

    set_user_skill(vol_chris, skill_beach, 5)
    set_user_skill(vol_chris, skill_debris, 3)

    set_user_skill(vol_dora, skill_food, 5)
    set_user_skill(vol_dora, skill_logistics, 3)

    # -------- 6. 建立三個實際任務（TASK_EVENT） --------
    today = date.today()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)

    # (1) 災區物資打包任務
    event_relief = create_event(
        owner_id=org_tc_id,
        org_id=org_tdrc,
        venue_id=venue_warehouse,
        event_date=today,
        start_hour=9,
        end_hour=12,         # 3 小時
        capacity=3,          # 故意設小一點，等下可以測候補
        title="災區物資打包任務",
        description="在台中倉庫協助分類、打包、搬運救災物資。",
        status="Planned",
    )
    set_event_periods(event_relief, [9, 10, 11])
    set_required_skills(
        event_relief,
        {
            "Logistics": 2,
            "Debris Removal": 1,
            "Food Distribution": 1,
        },
    )

    # (2) 台南淨灘行動
    event_beach = create_event(
        owner_id=org_tn_id,
        org_id=org_coast,
        venue_id=venue_beach,
        event_date=tomorrow,
        start_hour=8,
        end_hour=11,
        capacity=10,
        title="台南海灘環境淨灘",
        description="撿拾海漂垃圾、分類資源，維護海岸環境。",
        status="Planned",
    )
    set_event_periods(event_beach, [8, 9, 10])
    set_required_skills(
        event_beach,
        {
            "Beach Cleaning": 2,
            "Debris Removal": 1,
        },
    )

    # (3) 高雄收容所支援
    event_shelter = create_event(
        owner_id=org_kh_id,
        org_id=org_food,
        venue_id=venue_shelter,
        event_date=day_after,
        start_hour=13,
        end_hour=16,
        capacity=5,
        title="高雄臨時收容所支援",
        description="協助收容所餐食發放、動線引導與人流管制。",
        status="Planned",
    )
    set_event_periods(event_shelter, [13, 14, 15])
    set_required_skills(
        event_shelter,
        {
            "Food Distribution": 2,
            "Crowd Management": 2,
            "First Aid": 1,
        },
    )

    # -------- 7. 順便幫幾位志工報名，製造 Participation + Waitlist 資料 --------
    # 災區物資任務容量只有 3，人數報 4 個 → 會產生候補
    join_task(vol_anna, event_relief)
    join_task(vol_bob, event_relief)
    join_task(vol_chris, event_relief)
    wait_status = join_task(vol_dora, event_relief)  # 理論上會是 waitlisted

    print("✅ Disaster / cleanup seed data inserted.")
    print("  event_relief  id =", event_relief)
    print("  event_beach   id =", event_beach)
    print("  event_shelter id =", event_shelter)
    print("  wait_status for dora on relief =", wait_status)

    # 追加大量資料
    seed_bulk_data()
    # 追加一些假搜尋紀錄，方便 Admin 查看熱門關鍵字
    seed_dummy_logs(100)


if __name__ == "__main__":
    seed_disaster_data()
