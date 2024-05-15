import csv
import os
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

start = time.perf_counter()

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

file = open('books.csv', newline="")
reader = csv.DictReader(file)
counter=1

db.execute("CREATE TABLE books (isbn VARCHAR,title VARCHAR,author VARCHAR,year INTEGER)")
for row in reader:
    db.execute("INSERT INTO books (isbn,title,author,year) VALUES (:isbn, :title, :author, :year)", {
        "isbn": str(row["isbn"]), "title": row["title"].lower(), "author": row["author"].lower(), "year": row["year"]
    })
    print(f"\033[1;33;40m {str(counter)} ===> \033[1;32;40m {row['title'].lower()} >> we are at \033[1;31;40m   {str(counter)}")
    counter += 1
        
db.commit()
end = time.perf_counter()
print(f"\033[1;32;40m>>>>>>>>>>>TOOK \033[1;31;40M {end - start} sec \033[1;32;40m<<<<<<<<<<<<<")
