import sqlite3

def delete_messages():
    con = sqlite3.connect("db.sqlite3")
    cur = con.cursor()
    cur.execute('DELETE FROM django_migrations WHERE id=38')
    con.commit()
    cur.close()
    con.close()

delete_messages()
