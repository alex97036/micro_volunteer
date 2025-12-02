from db import get_conn

def test():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            print(cur.fetchone())

if __name__ == "__main__":
    test()