import cherrypy
import psycopg2
import tabulate

from util import say
from config import LOGFILE_NAME, DBNAME, DEFAULT_PORT

class EchoWebHandler():
    def __init__(self):
        self.db = psycopg2.connect(database=DBNAME)

    @cherrypy.expose
    def log(self):
        with open(LOGFILE_NAME) as lf:
            # seek 200k from the end
            lf.seek(0, 2)
            file_size = lf.tell()
            lf.seek(file_size-200000, 0)
            return "<h1>Most recent 200k of echo server log</h1>\n<pre>\n" + lf.read()

    @cherrypy.expose
    def summary(self):
        style = """
           <html>
           <head>
               <link rel="stylesheet" href="/echo-static/table.css">
           </head>
        """

        stmt = """
            SELECT
               nonce AS "Nonce",
               MIN(address) AS "IP Addr",
               MIN("time") AS "First Packet",
               MAX("time") AS "Last Packet",
               MAX(total_expected) AS "Packets Expected",
               COUNT(DISTINCT(packet_num)) AS "Unique Packets Received",
               COUNT(*) AS "Received Incl. Duplicates"
            FROM receptions
            GROUP BY nonce
            ORDER BY "First Packet" desc;
        """
        cursor = self.db.cursor()
        cursor.execute(stmt)
        result = cursor.fetchall()
        self.db.commit()
        return style + tabulate.tabulate(
            result,
            tablefmt='html',
            headers=[desc[0] for desc in cursor.description],
        )

def Start(args):
    cherrypy.config.update({
        'server.socket_host': '::',
        'server.socket_port': args.port - DEFAULT_PORT + 16000,
        'server.socket_timeout': 30,
    })
    cherrypy.quickstart(EchoWebHandler(), script_name='/echo')
    
