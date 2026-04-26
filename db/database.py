from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "vocalannotate.db")

Base = declarative_base()


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    annotations = relationship("Annotation", back_populates="book", cascade="all, delete-orphan")


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    page = Column(Integer, nullable=False)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    book = relationship("Book", back_populates="annotations")


engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def get_session():
    return Session()


# --- Book CRUD ---

def add_book(title: str) -> Book:
    session = get_session()
    book = Book(title=title.strip())
    session.add(book)
    session.commit()
    session.refresh(book)
    session.close()
    return book


def get_all_books():
    session = get_session()
    books = session.query(Book).order_by(Book.created_at).all()
    result = [{"id": b.id, "title": b.title} for b in books]
    session.close()
    return result


def delete_book(book_id: int):
    session = get_session()
    book = session.query(Book).filter_by(id=book_id).first()
    if book:
        session.delete(book)
        session.commit()
    session.close()


# --- Annotation CRUD ---

def add_annotation(book_id: int, page: int, note: str) -> Annotation:
    session = get_session()
    ann = Annotation(book_id=book_id, page=page, note=note.strip())
    session.add(ann)
    session.commit()
    ann_id = ann.id
    session.close()
    # Return a plain dict to avoid detached instance issues
    return {"id": ann_id, "page": page, "note": note.strip()}


def get_annotations_for_book(book_id: int):
    session = get_session()
    anns = (
        session.query(Annotation)
        .filter_by(book_id=book_id)
        .order_by(Annotation.page, Annotation.created_at)
        .all()
    )
    result = [{"id": a.id, "page": a.page, "note": a.note, "created_at": a.created_at} for a in anns]
    session.close()
    return result


def delete_annotation(ann_id: int):
    session = get_session()
    ann = session.query(Annotation).filter_by(id=ann_id).first()
    if ann:
        session.delete(ann)
        session.commit()
    session.close()
