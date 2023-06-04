from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# /charset='UTF8'
# firebird+fdb://login_on_firebird:password_on_firebird@localhost:3050/ + os.path.join(basedir, 'data.gdb')
engine = create_engine('firebird+fdb://SYSDBA:sysdba@127.0.0.1:3050/mtl')


DBSession = sessionmaker(bind=engine)
session = DBSession()
from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Base.metadata.bind = engine

# создаем модель таблицы связей таблиц author и publisher
author_publisher = Table(
    "author_publisher",
    Base.metadata,
    Column("author_id", Integer, ForeignKey("author.author_id")),
    Column("publisher_id", Integer, ForeignKey("publisher.publisher_id")),
)

# создаем модель таблицы связей таблиц book и publisher
book_publisher = Table(
    "book_publisher",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("book.book_id")),
    Column("publisher_id", Integer, ForeignKey("publisher.publisher_id")),
)


# определяем модельи классов для автора, книги и издательства
class Author(Base):
    __tablename__ = "author"
    author_id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    books = relationship("Book", backref=backref("author"))
    publishers = relationship(
        "Publisher", secondary=author_publisher, back_populates="authors"
    )


class Book(Base):
    __tablename__ = "book"
    book_id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey("author.author_id"))
    title = Column(String)
    publishers = relationship(
        "Publisher", secondary=book_publisher, back_populates="books"
    )


class Publisher(Base):
    __tablename__ = "publisher"
    publisher_id = Column(Integer, primary_key=True)
    name = Column(String)
    authors = relationship(
        "Author", secondary=author_publisher, back_populates="publishers"
    )
    books = relationship(
        "Book", secondary=book_publisher, back_populates="publishers"
    )


def update_db():
    Base.metadata.create_all(bind=engine)
    employee = session.query(Employee).filter(Employee.first_name == first_name, Employee.last_name == last_name).one()
    #metadata.create_all(engine)


if __name__ == "__main__":
    session.query()
    pass
