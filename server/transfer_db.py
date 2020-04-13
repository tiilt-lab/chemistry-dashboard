# -----------------------------------
# This is a transfer script designed
# for moving from SQLite3 to MySQL.
# -----------------------------------

from sqlalchemy import create_engine
sqlite_engine = create_engine('sqlite:///discussion_capture.db')
mysql_engine = create_engine("mysql+mysqlconnector://root:root@localhost:3306/discussion_capture")
sql_conn = sqlite_engine.connect()
mysql_conn = mysql_engine.connect()

# Transfer users.
result = sql_conn.execute("select * from user")
cmd = "INSERT INTO user VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
for row in result:
    mysql_conn.execute(cmd, row[0], row[1], row[2], row[3], row[4], str(row[5]), row[6], row[7], str(row[8]))

# Transfer devices.
result = sql_conn.execute("select * from device")
cmd = "INSERT INTO device VALUES (%s, %s, %s, %s, %s, %s, %s)"
for row in result:
    mysql_conn.execute(cmd, row[0], row[1], row[2], row[3], row[4], row[5], row[6])

# Transfer sessions.
result = sql_conn.execute("select * from session")
cmd = "INSERT INTO session VALUES (%s, %s, %s, %s, %s, %s)"
for row in result:
    mysql_conn.execute(cmd, row[0], row[1], row[2], str(row[3]), str(row[4]), None)

# Transfer Session Devices.
result = sql_conn.execute("select * from session_device")
cmd = "INSERT INTO session_device VALUES (%s, %s, %s, %s, %s, %s, %s)"
for row in result:
    mysql_conn.execute(cmd, row[0], row[1], row[2], row[3], row[4], row[5], row[6])

# Transfer transcripts.
result = sql_conn.execute("select * from transcript")
cmd = "INSERT INTO transcript VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
for row in result:
    mysql_conn.execute(cmd, row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12])

# Transfer keyword usages.
result = sql_conn.execute("select * from keyword_usage")
cmd = "INSERT INTO keyword_usage VALUES (%s, %s, %s, %s, %s)"
for row in result:
    mysql_conn.execute(cmd, row[0], row[1], row[2], row[3], row[4])

# Transfer keywords.
result = sql_conn.execute("select * from keyword")
cmd = "INSERT INTO keyword VALUES (%s, %s, %s)"
for row in result:
    mysql_conn.execute(cmd, row[0], row[1], row[2])

# Transfer keyword lists.
result = sql_conn.execute("select * from keyword_list")
cmd = "INSERT INTO keyword_list VALUES (%s, %s, %s, %s)"
for row in result:
    mysql_conn.execute(cmd, row[0], row[1], row[2], row[3])

# Transfer keyword list item.
result = sql_conn.execute("select * from keyword_list_item")
cmd = "INSERT INTO keyword_list_item VALUES (%s, %s)"
for row in result:
    mysql_conn.execute(cmd, row[0], row[1])

sql_conn.close()
mysql_conn.close()
sqlite_engine.dispose()
mysql_engine.dispose()