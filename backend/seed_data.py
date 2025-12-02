# backend/seed_data.py
from datetime import date
from db import get_conn
from volunteer import create_skill


def seed():
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. 建兩個主辦者 user（之後也可以當 organizer 用）
            cur.execute(
                """
                INSERT INTO "USER" (user_name, email, phone, password)
                VALUES
                  ('org_alice', 'alice@ngo.org', 12345678, 'pw'),
                  ('org_bob',   'bob@ngo.org',   87654321, 'pw')
                RETURNING user_id;
                """
            )
            rows = cur.fetchall()
            alice_id, bob_id = rows[0][0], rows[1][0]

            # 2. 給他們角色（Organizer）
            cur.execute(
                """
                INSERT INTO USER_ROLE (user_id, role)
                VALUES
                  (%s, 'Organizer'),
                  (%s, 'Organizer')
                """,
                (alice_id, bob_id),
            )

            # 3. 建兩個主辦單位 ORG
            cur.execute(
                """
                INSERT INTO ORG (org_name, contact_email)
                VALUES
                  ('City Animal Rescue', 'contact@animal.org'),
                  ('Book For Kids',      'hello@books.org')
                RETURNING org_id;
                """
            )
            org_rows = cur.fetchall()
            animal_org_id, book_org_id = org_rows[0][0], org_rows[1][0]
            # 綁定 organizer 與 ORG
            cur.execute(
                """
                INSERT INTO ORGANIZER_ORG (user_id, org_id)
                VALUES
                  (%s, %s),
                  (%s, %s)
                ON CONFLICT (user_id, org_id) DO NOTHING;
                """,
                (alice_id, animal_org_id, bob_id, book_org_id),
            )

            # 4. 建兩個場地 VENUE
            cur.execute(
                """
                INSERT INTO VENUE (name, address, capacity)
                VALUES
                  ('公園舞台', 'Taipei City Park', 10),
                  ('圖書教室', 'Taipei Library 3F', 8)
                RETURNING venue_id;
                """
            )
            venue_rows = cur.fetchall()
            park_id, classroom_id = venue_rows[0][0], venue_rows[1][0]

            # 5. 建幾個技能
            skill_photography = create_skill("Photography")
            skill_first_aid = create_skill("First Aid")
            skill_logistics = create_skill("Logistics")

            # 6. 建兩個任務 TASK_EVENT
            today = date.today()

            # 任務 1：動物認養活動
            cur.execute(
                """
                INSERT INTO TASK_EVENT
                  (owner_id, org_id, venue_id,
                   event_date, start_hour, end_hour, capacity, duration_hours,
                   status, title, description)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s,
                   'Planned', '動物認養說明會', '協助現場布置與解說')
                RETURNING event_id;
                """,
                (alice_id, animal_org_id, park_id,
                 today, 9, 11, 5, 2),
            )
            event1_id = cur.fetchone()[0]

            # 任務 2：兒童閱讀陪伴
            cur.execute(
                """
                INSERT INTO TASK_EVENT
                  (owner_id, org_id, venue_id,
                   event_date, start_hour, end_hour, capacity, duration_hours,
                   status, title, description)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s,
                   'Planned', '兒童閱讀陪伴', '陪小朋友閱讀與活動')
                RETURNING event_id;
                """,
                (bob_id, book_org_id, classroom_id,
                 today, 14, 16, 3, 2),
            )
            event2_id = cur.fetchone()[0]

            # 7. 設定任務時間區段 TASK_EVENT_PERIOD
            # 任務1: 09~11
            cur.execute(
                """
                INSERT INTO TASK_EVENT_PERIOD (event_id, period_hour)
                VALUES
                  (%s, 9),
                  (%s, 10);
                """,
                (event1_id, event1_id),
            )

            # 任務2: 14~16
            cur.execute(
                """
                INSERT INTO TASK_EVENT_PERIOD (event_id, period_hour)
                VALUES
                  (%s, 14),
                  (%s, 15);
                """,
                (event2_id, event2_id),
            )

            # 8. 任務所需技能 TASK_REQUIRED_SKILL
            cur.execute(
                """
                INSERT INTO TASK_REQUIRED_SKILL (event_id, skill_id, weight)
                VALUES
                  (%s, %s, 2),  -- 動物活動需要 Logistics
                  (%s, %s, 1),
                  (%s, %s, 2),  -- 閱讀活動需要 First Aid + Logistics
                  (%s, %s, 1);
                """,
                (event1_id, skill_logistics,
                 event1_id, skill_photography,
                 event2_id, skill_first_aid,
                 event2_id, skill_logistics),
            )

    print("✅ Seed data inserted.")
    print("  event1_id =", event1_id)
    print("  event2_id =", event2_id)


if __name__ == "__main__":
    seed()
