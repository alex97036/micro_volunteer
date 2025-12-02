-- 先把舊的表通通刪掉（如果不存在就忽略）
DROP TABLE IF EXISTS WAITLIST CASCADE;
DROP TABLE IF EXISTS MATCH_SCORE CASCADE;
DROP TABLE IF EXISTS TASK_REQUIRED_SKILL CASCADE;
DROP TABLE IF EXISTS USER_SKILL CASCADE;
DROP TABLE IF EXISTS SKILL CASCADE;
DROP TABLE IF EXISTS PARTICIPATION CASCADE;
DROP TABLE IF EXISTS TASK_EVENT_PERIOD CASCADE;
DROP TABLE IF EXISTS TASK_EVENT CASCADE;
DROP TABLE IF EXISTS VENUE CASCADE;
DROP TABLE IF EXISTS ORG CASCADE;
DROP TABLE IF EXISTS ORGANIZER_ORG CASCADE;
DROP TABLE IF EXISTS USER_ROLE CASCADE;
DROP TABLE IF EXISTS "USER" CASCADE;

-------------------------------------------------
-- 1. USER
-------------------------------------------------
CREATE TABLE "USER" (
    user_id      BIGSERIAL PRIMARY KEY,
    user_name    VARCHAR(20) NOT NULL UNIQUE,
    email        VARCHAR(50),
    phone        INT NOT NULL,
    password     VARCHAR(60) NOT NULL
);

-------------------------------------------------
-- 2. USER_ROLE
-------------------------------------------------
CREATE TABLE USER_ROLE (
    user_id  BIGINT NOT NULL,
    role     VARCHAR(10) NOT NULL,
    PRIMARY KEY (user_id, role),
    CONSTRAINT fk_user_role_user
        FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-------------------------------------------------
-- 3. ORG
-------------------------------------------------
CREATE TABLE ORG (
    org_id        BIGSERIAL PRIMARY KEY,
    org_name      VARCHAR(100) NOT NULL,
    contact_email VARCHAR(100) NOT NULL
);

-- Organizer 與 ORG 的對應（誰可以管理哪些主辦單位）
CREATE TABLE ORGANIZER_ORG (
    user_id BIGINT NOT NULL,
    org_id  BIGINT NOT NULL,
    PRIMARY KEY (user_id, org_id),
    CONSTRAINT fk_oo_user
        FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_oo_org
        FOREIGN KEY (org_id)
        REFERENCES ORG(org_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-------------------------------------------------
-- 4. VENUE
-------------------------------------------------
CREATE TABLE VENUE (
    venue_id BIGSERIAL PRIMARY KEY,
    name     VARCHAR(50)  NOT NULL,
    address  VARCHAR(200) NOT NULL,
    capacity INT          NOT NULL,
    CONSTRAINT chk_venue_capacity CHECK (capacity > 0)
);

-------------------------------------------------
-- 5. TASK_EVENT
-------------------------------------------------
CREATE TABLE TASK_EVENT (
    event_id       BIGSERIAL PRIMARY KEY,
    owner_id       BIGINT NOT NULL,
    org_id         BIGINT,
    venue_id       BIGINT NOT NULL,
    event_date     DATE   NOT NULL,
    start_hour     INT    NOT NULL, -- 0~23
    end_hour       INT    NOT NULL, -- 1~23，需大於 start_hour
    capacity       INT    NOT NULL,
    duration_hours INT    NOT NULL, -- = end_hour - start_hour
    status         VARCHAR(10) NOT NULL,
    title          VARCHAR(80),
    description    VARCHAR(300),

    CONSTRAINT chk_event_capacity       CHECK (capacity > 0),
    CONSTRAINT chk_event_duration_hours CHECK (duration_hours BETWEEN 1 AND 3),
    CONSTRAINT chk_event_hours          CHECK (start_hour BETWEEN 0 AND 23 AND end_hour BETWEEN 1 AND 23 AND end_hour > start_hour),
    CONSTRAINT chk_event_status         CHECK (status IN ('Planned','Ongoing','Finished')),
    CONSTRAINT chk_event_duration_match CHECK (end_hour - start_hour = duration_hours),

    CONSTRAINT fk_task_event_owner
        FOREIGN KEY (owner_id)
        REFERENCES "USER"(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_task_event_org
        FOREIGN KEY (org_id)
        REFERENCES ORG(org_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_task_event_venue
        FOREIGN KEY (venue_id)
        REFERENCES VENUE(venue_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-------------------------------------------------
-- 6. TASK_EVENT_PERIOD
-------------------------------------------------
CREATE TABLE TASK_EVENT_PERIOD (
    event_id    BIGINT NOT NULL,
    period_hour INT    NOT NULL,  -- 0~23
    PRIMARY KEY (event_id, period_hour),
    CONSTRAINT chk_period_hour CHECK (period_hour BETWEEN 0 AND 23),
    CONSTRAINT fk_period_event
        FOREIGN KEY (event_id)
        REFERENCES TASK_EVENT(event_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-------------------------------------------------
-- 7. PARTICIPATION
-------------------------------------------------
CREATE TABLE PARTICIPATION (
    user_id   BIGINT NOT NULL,
    event_id  BIGINT NOT NULL,
    join_time TIMESTAMP NOT NULL,
    role      VARCHAR(10) NOT NULL,  -- Volunteer / Lead
    status    VARCHAR(10) NOT NULL,  -- Active / Cancelled
    PRIMARY KEY (user_id, event_id),
    CONSTRAINT chk_part_role   CHECK (role IN ('Volunteer','Lead')),
    CONSTRAINT chk_part_status CHECK (status IN ('Active','Cancelled')),
    CONSTRAINT fk_part_user
        FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_part_event
        FOREIGN KEY (event_id)
        REFERENCES TASK_EVENT(event_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-------------------------------------------------
-- 8. SKILL
-------------------------------------------------
CREATE TABLE SKILL (
    skill_id   BIGSERIAL PRIMARY KEY,
    skill_name VARCHAR(60) NOT NULL UNIQUE
);

-------------------------------------------------
-- 9. USER_SKILL
-------------------------------------------------
CREATE TABLE USER_SKILL (
    user_id  BIGINT NOT NULL,
    skill_id BIGINT NOT NULL,
    level    INT    NOT NULL,  -- 1~5
    PRIMARY KEY (user_id, skill_id),
    CONSTRAINT chk_user_skill_level CHECK (level BETWEEN 1 AND 5),
    CONSTRAINT fk_user_skill_user
        FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_user_skill_skill
        FOREIGN KEY (skill_id)
        REFERENCES SKILL(skill_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-------------------------------------------------
-- 10. TASK_REQUIRED_SKILL
-------------------------------------------------
CREATE TABLE TASK_REQUIRED_SKILL (
    event_id BIGINT NOT NULL,
    skill_id BIGINT NOT NULL,
    weight   INT    NOT NULL DEFAULT 1,
    PRIMARY KEY (event_id, skill_id),
    CONSTRAINT chk_trs_weight CHECK (weight >= 1),
    CONSTRAINT fk_trs_event
        FOREIGN KEY (event_id)
        REFERENCES TASK_EVENT(event_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_trs_skill
        FOREIGN KEY (skill_id)
        REFERENCES SKILL(skill_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-------------------------------------------------
-- 11. MATCH_SCORE
-------------------------------------------------
CREATE TABLE MATCH_SCORE (
    user_id    BIGINT NOT NULL,
    event_id   BIGINT NOT NULL,
    score      NUMERIC(5,2) NOT NULL,
    updated_at TIMESTAMP    NOT NULL,
    PRIMARY KEY (user_id, event_id),
    CONSTRAINT chk_match_score CHECK (score BETWEEN 1 AND 5),
    CONSTRAINT fk_match_user
        FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_match_event
        FOREIGN KEY (event_id)
        REFERENCES TASK_EVENT(event_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-------------------------------------------------
-- 12. WAITLIST
-------------------------------------------------
CREATE TABLE WAITLIST (
    user_id    BIGINT NOT NULL,
    event_id   BIGINT NOT NULL,
    position   INT    NOT NULL,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, event_id),
    CONSTRAINT chk_waitlist_position CHECK (position >= 1),
    CONSTRAINT fk_wait_user
        FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_wait_event
        FOREIGN KEY (event_id)
        REFERENCES TASK_EVENT(event_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
