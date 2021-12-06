from cs50 import SQL

db = SQL("sqlite:///finance.db")

datetime = db.execute("SELECT datetime('now')")

print(datetime)

db.execute("INSERT into history(first) VALUES(:first)", first=datetime[0]["datetime('now')"])
