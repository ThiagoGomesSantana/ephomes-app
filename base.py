import sqlite3
from os import path
HOME = path.dirname(path.realpath(__file__))

class Conn:
    def __init__(self):
        if not path.isfile(f'{HOME}/database.db'):
            self.connect()
            self.build()
            
        self.connect()

    def connect(self):
        self.conn = sqlite3.connect(f'{HOME}/database.db')
        self.cur = self.conn.cursor()

    def close(self, reset=True):
        self.conn.close()
        if reset:
            self.connect()

    def insert_redfin(self, data, fresh):
        if fresh:
            self.clear_redfin()

        self.cur.executemany("""
            INSERT OR REPLACE INTO redfin(ADDRESS, LOT_AREA, PRICE, KIND)
            VALUES(?,?,?,?);""", data)
        self.conn.commit()
        self.close()

    def insert_portland(self, address, owner, zoning, url, property_type):
        self.cur.execute("""
            UPDATE redfin
            SET OWNER = ?,
                ZONING = ?,
                URL = ?,
                PROPERTY_TYPE = ?
            WHERE ADDRESS = ?;""", (owner, zoning, url, property_type, address))
        self.conn.commit()
        self.close()

    def insert_portland_url(self, address, url):
        self.cur.execute("""
            UPDATE redfin
            SET URL = ?
            WHERE ADDRESS = ?;""", (url, address))
        self.conn.commit()
        self.close()

    def clear_redfin(self):
        self.cur.execute("""DELETE FROM redfin""")
        self.conn.commit()
        self.close()

    def get_address(self):
        self.cur.execute("""SELECT ADDRESS FROM redfin""")
        res = list(map(lambda x: x[0], self.cur.fetchall()))
        return res

    def build(self):
        self.cur.execute("""
            CREATE TABLE redfin(
                ADDRESS TEXT UNIQUE,
                URL TEXT,
                OWNER TEXT,
                LOT_AREA TEXT,
                ZONING TEXT,
                PRICE TEXT,
                PROPERTY_TYPE TEXT,
                KIND TEXT
            );
        """)
        self.conn.commit()
        print('database iniciada com sucesso')
        self.close()

    def get_data(self):
        self.cur.execute("""SELECT * FROM redfin""")
        res = self.cur.fetchall()
        return res

    def get_data_table(self):
        self.cur.execute("""SELECT * FROM redfin""")
        res = self.cur.fetchall()
        table=[]
        for row in res:
            address = row[0]
            url = row[1]
            owner = row[2] or '—'
            lot_area = row[3]
            if lot_area != '—':
                lot_area = row[3].replace(',','')+'.0 sqft'
            zoning = row[4] or '—'
            price = row[5]+'.0'
 
            table.append({
                'address': address,
                'url': url,
                'owner': owner,
                'lot_area': lot_area,
                'zoning': zoning,
                'price': price})
            
        return table