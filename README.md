# Micro Volunteer Project 使用指南

## 前置安裝
- 安裝 PostgreSQL，確保有 `psql`，預設連線：
  - 主機：`localhost`
  - 連接埠：`5432`
  - 使用者：`alexhsu`（或依實際情況修改 `backend/db.py` 的 `DB_CONFIG`）
  - 資料庫名稱：`micro_volunteer`
- 安裝 Python 3.9+，並建立虛擬環境：
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- 安裝相依套件：
  ```bash
  pip install psycopg psycopg[binary] tinydb
  ```

## 建立資料庫
1. 在 PostgreSQL 建立資料庫（若尚未建立）：
   ```bash
   createdb micro_volunteer
   ```
2. 初始化資料表（會 DROP 既有表，請小心）：
   ```bash
   python3 backend/init_schema.py
   ```
3. 匯入種子資料（含大量假資料與假搜尋紀錄）：
   ```bash
   python3 backend/seed_disaster_data.py
   ```
   - 內容：基本的 Organizer/ORG/場地/技能/任務、志工、報名/候補資料，以及 1 萬志工、100 任務等大量測試資料，並寫入 TinyDB 的假搜尋紀錄 `data/analytics.json`。

## 主要執行檔
- `backend/server.py`
  - TCP 伺服器（127.0.0.1:5050），處理註冊/登入、任務查詢/報名/取消/歷史紀錄、Organizer 建任務/場地/需求技能/場地占用查詢、Admin 刪除資料、NoSQL 熱門關鍵字查詢等。
  - 預設會建立 Admin 帳號 `alex / 1234`（具 Admin/Organizer/Volunteer 三個角色）。
- `backend/client.py`
  - 志工/Organizer CLI。志工可搜尋未來/歷史任務、報名/取消、查看歷史紀錄、查看已報名任務、更新個資；Organizer 可建場地/ORG/任務、設定時間與技能、查看任務報名名單、查場地時段是否可用。
- `backend/admin_cli.py`
  - Admin 管理介面：列出/過濾使用者角色、增刪角色（可授予 Admin）、增刪 ORG/場地/技能/任務，並查看 NoSQL 熱門搜尋關鍵字。

## 執行步驟
1. 啟動伺服器（需先啟動 PostgreSQL）：
   ```bash
   python3 backend/server.py
   ```
   看到 `[SERVER] Listening on 127.0.0.1:5050 ...` 表示成功。
2. 開新終端啟動志工/Organizer 客戶端：
   ```bash
   python3 backend/client.py
   ```
   - 可選既有帳號登入或註冊（志工/Organizer）。
   - 搜尋任務時，預設僅顯示未來且未結束的任務；另有「搜尋歷史任務」選項。
3. 開新終端啟動 Admin 介面：
   ```bash
   python3 backend/admin_cli.py
   ```
   - 用帳號 `alex` / 密碼 `1234` 登入。
   - 可查看/管理角色、刪除任務/場地/技能、查看熱門搜尋關鍵字（來自 TinyDB）。

## NoSQL（TinyDB）記錄
- 檔案：`data/analytics.json`
- 內容：`search_logs` 表，記錄搜尋關鍵字、條件、使用者與時間戳。
- 種子：`seed_disaster_data.py` 已自動寫入假搜尋紀錄；可用 Admin 選單「查看熱門搜尋關鍵字」查看。

## 常用資料庫指令（psql）
```sql
-- 列出表
\dt
-- 查看表結構
\d "USER"
-- 任務列表
SELECT event_id, title, event_date, start_hour, end_hour, status FROM TASK_EVENT LIMIT 10;
-- 某使用者的參與紀錄
SELECT * FROM PARTICIPATION WHERE user_id = 1;
```

## 注意事項
- 重新執行 `init_schema.py` 會清空資料，請先備份需要的資料。
- 搜尋/報名/取消等請求都會在 server 側加鎖處理，以避免併發超額。 NoSQL 只用於搜尋分析，與主資料一致性無關。
