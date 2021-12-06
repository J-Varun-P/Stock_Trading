import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user = db.execute("SELECT * from users WHERE id=:id", id=session["user_id"])
    rows=[]
    c1 = 0
    c3 = 0
    if len(user) != 0:
        username = user[0]["username"]
        rows = db.execute("SELECT * from latest WHERE username=:username", username=username)
        chand = db.execute("SELECT * from users WHERE username=:username", username=username)
        c2 = chand[0]["cash"]
        c3 = c2
        for row in rows:
            temp = lookup(row["symbol"])
            c1 += (temp["price"] * row["quantity"])
            db.execute("UPDATE latest SET price=:price WHERE symbol=:symbol", price=temp["price"], symbol=row["symbol"])
        return render_template("index.html", rows=rows, c1=c1, c2=c2)
    c2 = c3
    return render_template("index.html", rows=rows, c1=c1, c2=c2)
    #return apology("TODO main page")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        if not request.form.get("symbol"):
            return apology("please select a stock's symbol")
        elif not request.form.get("shares"):
            return apology("please select number of shares")
        else:
            user = db.execute("SELECT * from users WHERE id=:id", id=session["user_id"])
            username = user[0]["username"]
            row = lookup(request.form.get("symbol"))
            cost = row["price"]
            price = cost * int(request.form.get("shares"))
            current_amount = user[0]["cash"]
            if price > current_amount:
                return apology("You don't have enough cash")
            else:
                datetime = db.execute("SELECT datetime('now')")
                db.execute("UPDATE users SET cash =:cash WHERE id=:id", cash=user[0]["cash"] - price, id=session["user_id"])
                company = lookup(request.form.get("symbol").upper())
                c_name = company["name"]
                temp = db.execute("SELECT * from buy where symbol=:symbol and username=:username", symbol=request.form.get("symbol").upper(), username=username)
                if len(temp) == 0:
                    db.execute("INSERT into buy(username, symbol, quantity, price, name) VALUES(:username, :symbol, :quantity, :price, :c_name)", username=username, symbol=request.form.get("symbol").upper(), quantity=request.form.get("shares"), price=cost, c_name=c_name)
                    db.execute("INSERT into latest(username, symbol, quantity, price, name) VALUES(:username, :symbol, :quantity, :price, :c_name)", username=username, symbol=request.form.get("symbol").upper(), quantity=request.form.get("shares"), price=cost, c_name=c_name)
                else:
                    quantity = temp[0]["quantity"]
                    db.execute("UPDATE buy SET quantity=:quantity where symbol=:symbol and username=:username", quantity=quantity+int(request.form.get("shares")), symbol=request.form.get("symbol").upper(), username=username)
                    db.execute("UPDATE latest SET quantity=:quantity where symbol=:symbol and username=:username", quantity=quantity+int(request.form.get("shares")), symbol=request.form.get("symbol").upper(), username=username)
                db.execute("INSERT into history(username, symbol, quantity, price, transacted) VALUES(:username, :symbol, :quantity, :price, :transacted)", username=username, symbol=request.form.get("symbol").upper(), quantity=request.form.get("shares"), price=cost, transacted=datetime[0]["datetime('now')"] )
                return redirect("/")
    #return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user = db.execute("SELECT * from users WHERE id=:id", id=session["user_id"])
    username = user[0]["username"]
    rows = db.execute("SELECT * from history WHERE username=:username", username=username)
    return render_template("history.html", rows=rows)
    #return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("please enter a stock's symbol")
        row = lookup(symbol)
        if row == None:
            return apology("please enter a valid stock's symbol")
        name = row["name"]
        symbol = row["symbol"]
        price = row["price"]
        return render_template("quoted.html", name=name, symbol=symbol, price=price)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password and confirmation password don't match", 403)

        rows = db.execute("SELECT * from users WHERE username = :username", username=request.form.get("username"))

        if len(rows) == 1:
            return apology("username taken, please select another one", 403)
        else:
            password = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)
            db.execute("INSERT into users(username, hash) VALUES(:username, :password)", username=request.form.get("username"), password=password)
            db.execute("INSERT into participants(username, valuation) VALUES(:username, :valuation)", username=request.form.get("username"), valuation=0)
            return redirect("/login")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    temp = db.execute("SELECT * from users WHERE id=:id", id=session["user_id"])
    cash = temp[0]["cash"]
    username = temp[0]["username"]
    if request.method == "GET":
        menu = []
        rows = db.execute("SELECT * from buy where username=:username", username=username)
        for row in rows:
            menu.append(row["symbol"])
        return render_template("sell.html", menu=menu)
    else:
        if not request.form.get("symbol"):
            return apology("please provide an input for a stock")
        else:
            n = int(request.form.get("shares"))
            if n <= 0:
                return apology("please provide a positive number")
            rows = db.execute("SELECT * from buy WHERE username=:username and symbol =:symbol", username=username, symbol=request.form.get("symbol"))
            current = int(rows[0]["quantity"])
            if n > current:
                return apology("you don't have the provided number of shares")
            else:
                temp1 = lookup(request.form.get("symbol"))
                c_price = temp1["price"]
                db.execute("UPDATE users SET cash=:cash where username=:username", cash = cash + (c_price * n), username=username)
                if n == current:
                    db.execute("DELETE from buy WHERE username=:username and symbol=:symbol", username=username, symbol=request.form.get("symbol"))
                    db.execute("DELETE from latest WHERE username=:username and symbol=:symbol", username=username, symbol=request.form.get("symbol"))
                else:
                    db.execute("UPDATE buy SET quantity=:quantity where username=:username and symbol=:symbol", quantity = int(rows[0]["quantity"]) - n, username=username, symbol=request.form.get("symbol"))
                    db.execute("UPDATE latest SET quantity=:quantity where username=:username and symbol=:symbol", quantity = int(rows[0]["quantity"]) - n, username=username, symbol=request.form.get("symbol"))
                n = -n
                datetime = db.execute("SELECT datetime('now')")
                db.execute("INSERT into history(username, symbol, quantity, price, transacted) VALUES(:username, :symbol, :quantity, :price, :transacted)", username=username, symbol=request.form.get("symbol").upper(), quantity=n, price=c_price, transacted=datetime[0]["datetime('now')"] )
                return redirect("/")
    #return apology("TODO")


@app.route("/participants")
@login_required
def participants():
    rows = db.execute("SELECT * from participants")
    for row in rows:
        username = row["username"]
        current = 0
        temps = db.execute("SELECT * from buy where username=:username", username=username)
        for temp in temps:
            cx = lookup(temp["symbol"])
            cy = cx["price"]
            current += (cy * temp["quantity"])
        cz = (db.execute("SELECT * from users where username=:username", username=username))
        current += cz[0]["cash"]
        db.execute("UPDATE participants SET valuation=:valuation where username=:username", valuation=current, username=username)
    rows = db.execute("SELECT * from participants order by valuation DESC")
    return render_template("participants.html", rows=rows)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
