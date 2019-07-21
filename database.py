import sqlite3

def selectDataObjects(query, location):
    temp = r'./_init/%s.db' % location
    conn = sqlite3.connect(temp, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = conn.cursor()
    cur.execute(query)
    col = cur.fetchall()
    return col
