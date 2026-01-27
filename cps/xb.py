from . import constants, logger
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session

log = logger.create()

Base = declarative_base()

# define the Media table 
class Media(Base):
    __tablename__ = 'media'
    id = Column(Integer, primary_key=True)
    playlists_id = Column(Integer)
    size = Column(Integer)
    duration = Column(Float)
    time_created = Column(DateTime)
    time_modified = Column(DateTime)
    time_deleted = Column(DateTime)
    time_downloaded = Column(DateTime)
    fps = Column(Float)
    view_count = Column(Integer)
    path = Column(String)
    webpath = Column(String)
    extractor_id = Column(String)
    title = Column(String)
    uploader = Column(String)
    live_status = Column(String)
    error = Column(String)
    time_uploaded = Column(DateTime)
    width = Column(Integer)
    height = Column(Integer)
    type = Column(String)
    video_codecs = Column(String)
    audio_codecs = Column(String)
    subtitle_codecs = Column(String)
    video_count = Column(Integer)
    audio_count = Column(Integer)
    language = Column(String)
    subtitle_count = Column(Integer)
    download_attempts = Column(Integer)

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
        media_entry = session.query(Caption).filter(Caption.id == caption).first()
        if not media_entry:
            log.error(f"No media found for caption id: {caption}")
            return None

        book_entry = session.query(BookMediaMapping).filter(BookMediaMapping.media_id == media_entry.media_id).first()
        if not book_entry:
            log.error(f"No book mapping found for media id: {media_entry.media_id}")
            return None

        return book_entry.book_id
    except Exception as e:
        log.error(f"Error getting book for caption: {e}")
    finally:
        session.close()
