import os
import requests
import json

from flask_bcrypt import Bcrypt
from flask import Flask, session, render_template, request, redirect, url_for
from flask_session import Session
from flask_api import status
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
 
@app.route("/")
def index():
    session["logged"] = False
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    if request.form.get("username") is None or request.form.get("password") is None:
        return render_template("index.html", error="All fields are necessary")

    users = db.execute("SELECT * FROM users WHERE username=:username", {
        "username": request.form.get("username")
    }).fetchone()

    if users is None:
            return render_template("index.html", error="username not found"), 404

    if bcrypt.check_password_hash(users.password, request.form.get("password")):
        session['username'] = request.form.get("username")        
        session['logged'] = True
        books = db.execute("SELECT * FROM books").fetchall()
        return render_template("logged.html", books=books, title="Home", header="All books")
    return render_template("error.html", error="wrong password")

@app.route("/sign-up", methods=["POST"])
def sign_up():
    if request.form.get("username") is None or request.form.get("password") is None or request.form.get("re-password") is None:
        return render_template("index.html", error="All fields are necessary")
    
    if request.form.get("password") != request.form.get("re-password"):
        return render_template("index.html", error="inmatching passwords")

    users = db.execute("SELECT username FROM users WHERE username=:user", {
        "user": request.form.get("username")
    }).fetchone()

    if users is None:
        hashed = bcrypt.generate_password_hash(request.form.get("password")).decode("utf-8")
        db.execute("INSERT INTO users (username, password, review_count) VALUES (:username, :password, :review_count)", {
            "username": request.form.get("username"),
            "password": hashed,
            "review_count": 0
        })
        db.commit()
        return render_template("index.html", error="signed up as " + request.form.get("username"))
    return render_template("index.html", error="username taken")

@app.route("/logged.html", methods=["GET"])
def logged():
    if session['logged'] == False:
        return render_template("error.html", error="invalid access")
    books=db.execute("SELECT * FROM books").fetchall()
    return render_template("logged.html", books=books, title="Home", header="All books")

@app.route("/<string:title>", methods=["GET","POST"])
def book(title):
    if session['logged'] == False:
        return render_template("error.html", error="invalid access")
    if request.method == "GET":
        book=db.execute("SELECT * FROM books WHERE title=:title LIMIT 1", {
            "title":title.lower()
        }).fetchone()

        reviews=db.execute("SELECT * FROM reviews WHERE title=:title", {
            "title":title.lower()
        }).fetchall()

        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={
            "key": "92iSkN6TkcrQJvoQfXzA",
            "isbns": book.isbn
            })
        return render_template("book.html", book=book, title=title, res=res.json(), reviews=reviews, error="")
    else:
        check=db.execute("SELECT * FROM reviews WHERE title=:title AND username=:username",{
            "title":title,
            "username":session["username"]
        }).fetchone()
        if check is None:
            db.execute("INSERT INTO reviews (title, review, username) VALUES (:title, :review, :username)", {
                "title":title,
                "review":request.form.get("the-review"),
                "username":session["username"]
            })
            db.commit()
            return redirect(url_for('book', title=title))
        else:
            book=db.execute("SELECT * FROM books WHERE title=:title LIMIT 1", {
                "title":title.lower()
                }).fetchone()

            reviews=db.execute("SELECT * FROM reviews WHERE title=:title", {
                "title":title.lower()
                }).fetchall()

            res = requests.get("https://www.goodreads.com/book/review_counts.json", params={
                "key": "92iSkN6TkcrQJvoQfXzA",
                "isbns": book.isbn
                }) 
            return render_template("book.html", book=book, title=title, res=res.json(), reviews=reviews, error="you only allowed to submit one review")

@app.route("/search", methods=["POST"])
def search():
    if session['logged'] == False:
        return render_template("error.html", error="invalid access")
    try:
        len = len(request.form.get("the-search"))
        isbn_year = int(request.form.get("the-search"))
        if len > 4:
            books=db.execute("SELECT * FROM books WHERE isbn LIKE '%:isbn%' LIMIT 30",{
                "isbn":isbn-year.lower()
            }).fetchall()
        else:
            books=db.execute("SELECT * FROM books WHERE year LIKE '%:year%' LIMIT 30 ORDER BY year DESC",{
                "year":isbn-year
            }).fetchall()
    except:
        books=db.execute("SELECT * FROM books WHERE title LIKE :input OR author LIKE :input LIMIT 30",{
            "input": '%' + request.form.get("the-search").lower() + '%'
        }).fetchall()
    
    if books is None: 
        return render_template("error.html", error="404 NOT FOUND"), 404
    return render_template("logged.html", books=books, title="Search", header="Search results")

@app.route('/logout')
def logout():
    session['logged'] = False
    session["username"] = ""
    return render_template("index.html")

@app.route('/api/<isbn>')
def api(isbn):
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={
        "key": "92iSkN6TkcrQJvoQfXzA",
        "isbns": isbn
    })

    book=db.execute("SELECT * FROM books WHERE isbn=:isbn", {
        "isbn":isbn
    }).fetchall()

    if res.status_code == 404:
        return "ERROR 404 NOT FOUND",status.HTTP_404_NOT_FOUND
    
    res=res.json()
    data_set = {
        "title": book[0]['title'],
        "author": book[0]['author'],
        "year": book[0]['year'],
        "isbn": isbn,
        "review_count": res["books"][0]["ratings_count"],
        "average_score": res["books"][0]["average_rating"]
    }

    json_set=json.dumps(data_set)
    return json_set, status.HTTP_200_OK