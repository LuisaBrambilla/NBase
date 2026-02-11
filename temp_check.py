from db.db import get_connection

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT status, COUNT(*) AS total FROM norma WHERE origem='govbr' GROUP BY status ORDER BY status")
print(cur.fetchall())
cur.execute("SELECT COUNT(*) AS total FROM norma WHERE origem='govbr' AND consolidado = TRUE")
print("consolidado", cur.fetchone()["total"])
cur.close()
conn.close()
