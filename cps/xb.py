from . import constants, logger
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session

log = logger.create()

Base = declarative_base()

# define the Media table 
class Media(Base):
    __tablename__ = 'media'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String)
    path = Column(String)

    # Relationships
    captions = relationship("Caption", back_populates="media")

    def __repr__(self):
        return f"<Media(title='{self.title}', path='{self.path}')>"

# define the Caption table
class Caption(Base):
    __tablename__ = 'captions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(Integer, ForeignKey('media.id'))
    time = Column(Integer)
    text = Column(Text)

    # Relationships to Media
    media = relationship("Media", back_populates="captions")

# define the mapping table for book ids from metadata.db to media ids in xklb.db
class BookMediaMapping(Base):
    __tablename__ = 'book_media_map'
    book_id = Column(Integer, primary_key=True)
    media_id = Column(Integer, ForeignKey('media.id'))
    media = relationship("Media")

# create the engine and session maker
engine = create_engine(constants.XB_DB_PATH)
Session = scoped_session(sessionmaker(bind=engine))
Base.metadata.create_all(engine)

# function to map book ids to media ids
def add_book_media_mapping(book_id, media_id):
    session = Session()
    
    try:
        new_mapping = BookMediaMapping(book_id=book_id, media_id=media_id)
        session.add(new_mapping)
        session.commit()
    except Exception as e:
        log.error(f"Error adding book-media mapping: {e}")
        session.rollback()
    finally:
        session.close()

# function to get a specific book (which maps to a media entry) for a given caption
def get_book_for_caption(caption):
    session = Session()
    
    try:
        media_id = session.query(Caption).filter(Caption.id == caption).first().media_id
        book_id = session.query(BookMediaMapping).filter(BookMediaMapping.media_id == media_id).first().book_id
        return book_id
    except Exception as e:
        log.error(f"Error getting book for caption: {e}")
    finally:
        session.close()
