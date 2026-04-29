from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
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
    cover_path = Column(String(500), nullable=True)
    annotations = relationship("Annotation", back_populates="book", cascade="all, delete-orphan")
    themes = relationship("Theme", back_populates="book", cascade="all, delete-orphan")


class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    book = relationship("Book", back_populates="themes")
    annotations = relationship("Annotation", back_populates="theme")

    __table_args__ = (UniqueConstraint("book_id", "name", name="uq_book_theme"),)


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    page = Column(Integer, nullable=False)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=True)
    book = relationship("Book", back_populates="annotations")
    theme = relationship("Theme", back_populates="annotations")


engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def _migrate_existing_db():
    """Add columns to existing tables that were created before newer features existed."""
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info(annotations)")
        cols = [row[1] for row in result]
        if cols and "theme_id" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE annotations ADD COLUMN theme_id INTEGER REFERENCES themes(id)"
            )
            conn.commit()

        result = conn.exec_driver_sql("PRAGMA table_info(books)")
        cols = [row[1] for row in result]
        if cols and "cover_path" not in cols:
            conn.exec_driver_sql("ALTER TABLE books ADD COLUMN cover_path VARCHAR(500)")
            conn.commit()


_migrate_existing_db()
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
    result = [
        {"id": b.id, "title": b.title, "cover_path": b.cover_path}
        for b in books
    ]
    session.close()
    return result


def delete_book(book_id: int):
    session = get_session()
    book = session.query(Book).filter_by(id=book_id).first()
    if book:
        session.delete(book)
        session.commit()
    session.close()


def update_book_cover(book_id: int, cover_path):
    session = get_session()
    book = session.query(Book).filter_by(id=book_id).first()
    if book:
        book.cover_path = cover_path
        session.commit()
    session.close()


# --- Theme CRUD ---

def add_theme(book_id: int, name: str) -> dict:
    name = name.strip()[:100]
    if not name:
        raise ValueError("Theme name cannot be empty.")
    session = get_session()
    try:
        theme = Theme(book_id=book_id, name=name)
        session.add(theme)
        session.commit()
        return {"id": theme.id, "name": theme.name}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_themes_for_book(book_id: int) -> list:
    session = get_session()
    themes = session.query(Theme).filter_by(book_id=book_id).order_by(Theme.name).all()
    result = [{"id": t.id, "name": t.name} for t in themes]
    session.close()
    return result


def delete_theme(theme_id: int):
    session = get_session()
    # Manually null out annotations so they become Unclassified (preserves their data)
    anns = session.query(Annotation).filter_by(theme_id=theme_id).all()
    for ann in anns:
        ann.theme_id = None
    theme = session.query(Theme).filter_by(id=theme_id).first()
    if theme:
        session.delete(theme)
    session.commit()
    session.close()


def update_annotation_theme(ann_id: int, theme_id) -> None:
    session = get_session()
    ann = session.query(Annotation).filter_by(id=ann_id).first()
    if ann:
        ann.theme_id = theme_id
        session.commit()
    session.close()


# --- Annotation CRUD ---

def add_annotation(book_id: int, page: int, note: str, theme_id=None) -> dict:
    session = get_session()
    ann = Annotation(book_id=book_id, page=page, note=note.strip(), theme_id=theme_id)
    session.add(ann)
    session.commit()
    ann_id = ann.id
    session.close()
    return {"id": ann_id, "page": page, "note": note.strip(), "theme_id": theme_id}


def get_annotations_for_book(book_id: int, sort_by: str = "page", theme_filter=None) -> list:
    session = get_session()
    q = session.query(Annotation).filter_by(book_id=book_id)

    if theme_filter == "unclassified":
        q = q.filter(Annotation.theme_id == None)
    elif theme_filter is not None:
        q = q.filter(Annotation.theme_id == theme_filter)

    if sort_by == "newest":
        q = q.order_by(Annotation.created_at.desc())
    elif sort_by == "oldest":
        q = q.order_by(Annotation.created_at.asc())
    else:
        q = q.order_by(Annotation.page, Annotation.created_at)

    anns = q.all()
    result = []
    for a in anns:
        theme_name = a.theme.name if a.theme else None
        result.append({
            "id": a.id,
            "page": a.page,
            "note": a.note,
            "created_at": a.created_at,
            "theme_id": a.theme_id,
            "theme_name": theme_name,
        })
    session.close()
    return result


def delete_annotation(ann_id: int):
    session = get_session()
    ann = session.query(Annotation).filter_by(id=ann_id).first()
    if ann:
        session.delete(ann)
        session.commit()
    session.close()
