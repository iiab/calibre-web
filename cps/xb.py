import os
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, create_engine, exc
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from . import logger

log = logger.create()

session = None
xklb_DB_path = None
Base = declarative_base()

class Media(Base):
    __tablename__ = 'media'

    id = Column(Integer, primary_key=True)
    playlists_id = Column(Integer)
    size = Column(Integer)
    duration = Column(Integer)
    time_created = Column(Integer)
    time_modified = Column(Integer)
    time_deleted = Column(Integer)
    time_downloaded = Column(Integer)
    fps = Column(Integer)
    view_count = Column(Integer)
    path = Column(String)
    webpath = Column(String)
    extractor_id = Column(String)
    title = Column(String)
    uploader = Column(String)
    live_status = Column(String)
    error = Column(String)
    time_uploaded = Column(Integer)
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

    captions = relationship("Caption", back_populates="media")
    history = relationship("History", back_populates="media")

    def __repr__(self):
        return f"<Media(title='{self.title}', path='{self.path}')>"

class Caption(Base):
    __tablename__ = 'captions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(Integer, ForeignKey('media.id'))
    time = Column(Integer)
    text = Column(Text)

    media = relationship("Media", back_populates="captions")

    def __repr__(self):
        return f"<Caption(media_id={self.media_id}, time={self.time}, text={self.text})>"

class BookMediaMapping(Base):
    __tablename__ = 'book_media_map'

    book_id = Column(Integer, primary_key=True)
    media_id = Column(Integer, ForeignKey('media.id'))
    media = relationship("Media")

class History(Base):
    __tablename__ = 'history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(Integer, ForeignKey('media.id'))
    time_played = Column(Integer)
    done = Column(Boolean)

    media = relationship("Media", back_populates="history")

class Playlists(Base):
    __tablename__ = 'playlists'

    id = Column(Integer, primary_key=True)
    time_modified = Column(Integer)
    time_deleted = Column(Integer)
    time_created = Column(Integer)
    hours_update_delay = Column(Integer)
    path = Column(String)
    extractor_key = Column(String)
    profile = Column(String)
    extractor_config = Column(String)
    extractor_playlist_id = Column(String)
    title = Column(String)
    uploader = Column(String)

# Define the captions_fts, media_fts, playlists_fts (full-text search tables)
class CaptionsFTS(Base):
    __tablename__ = 'captions_fts'

    docid = Column(Integer, primary_key=True)
    text = Column(Text)

class MediaFTS(Base):
    __tablename__ = 'media_fts'

    docid = Column(Integer, primary_key=True)
    title = Column(Text)

class PlaylistsFTS(Base):
    __tablename__ = 'playlists_fts'

    docid = Column(Integer, primary_key=True)
    title = Column(Text)

# Define configuration tables for FTS (captions_fts_config, media_fts_config, playlists_fts_config)
class CaptionsFTSConfig(Base):
    __tablename__ = 'captions_fts_config'

    id = Column(Integer, primary_key=True)
    config_value = Column(String)

class MediaFTSConfig(Base):
    __tablename__ = 'media_fts_config'

    id = Column(Integer, primary_key=True)
    config_value = Column(String)

class PlaylistsFTSConfig(Base):
    __tablename__ = 'playlists_fts_config'

    id = Column(Integer, primary_key=True)
    config_value = Column(String)

# Define data tables for FTS (captions_fts_data, media_fts_data, playlists_fts_data)
class CaptionsFTSData(Base):
    __tablename__ = 'captions_fts_data'

    id = Column(Integer, primary_key=True)
    data = Column(Text)

class MediaFTSData(Base):
    __tablename__ = 'media_fts_data'

    id = Column(Integer, primary_key=True)
    data = Column(Text)

class PlaylistsFTSData(Base):
    __tablename__ = 'playlists_fts_data'

    id = Column(Integer, primary_key=True)
    data = Column(Text)

# Define document size tables for FTS (captions_fts_docsize, media_fts_docsize, playlists_fts_docsize)
class CaptionsFTSDocSize(Base):
    __tablename__ = 'captions_fts_docsize'

    id = Column(Integer, primary_key=True)
    docsize = Column(Integer)

class MediaFTSDocSize(Base):
    __tablename__ = 'media_fts_docsize'

    id = Column(Integer, primary_key=True)
    docsize = Column(Integer)

class PlaylistsFTSDocSize(Base):
    __tablename__ = 'playlists_fts_docsize'

    id = Column(Integer, primary_key=True)
    docsize = Column(Integer)

# Define FTS indexes (captions_fts_idx, media_fts_idx, playlists_fts_idx)
class CaptionsFTSIndex(Base):
    __tablename__ = 'captions_fts_idx'

    id = Column(Integer, primary_key=True)
    idx_value = Column(String)

class MediaFTSIndex(Base):
    __tablename__ = 'media_fts_idx'

    id = Column(Integer, primary_key=True)
    idx_value = Column(String)

class PlaylistsFTSIndex(Base):
    __tablename__ = 'playlists_fts_idx'

    id = Column(Integer, primary_key=True)
    idx_value = Column(String)

# SQLite statistics
# class SQLiteStat1(Base):
#     __tablename__ = 'sqlite_stat1'

#     tbl = Column(String, primary_key=True)
#     idx = Column(String)
#     stat = Column(String)

def get_book_for_caption(caption):
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

def add_book_media_mapping(book_id, media_id):
    try:
        book_media_mapping = BookMediaMapping(book_id=book_id, media_id=media_id)
        session.add(book_media_mapping)
        session_commit(f"Book-media mapping added for book id: {book_id}, media id: {media_id}")
    except Exception as e:
        log.error(f"Error adding book-media mapping: {e}")

def create_blank_database(engine):
    """Creates the database with the required schema."""
    Base.metadata.create_all(engine)
    log.info("New blank database created.")

def init_db(xklb_db_path):
    global session, xklb_DB_path
    xklb_DB_path = xklb_db_path

    engine = create_engine(f'sqlite:///{xklb_db_path}', echo=False)
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()

    if not os.path.exists(xklb_db_path):
        log.info(f"Database file not found at {xklb_db_path}, creating a new blank database.")
        create_blank_database(engine)
    else:
        try:
            Base.metadata.create_all(engine)
            log.info(f"Database file found at {xklb_db_path}.")
        except exc.SQLAlchemyError as e:
            log.error(f"Error ensuring tables exist in the database: {e}")

def dispose():
    global session
    old_session = session
    session = None
    if old_session:
        try:
            old_session.close()
        except Exception:
            pass
        if old_session.bind:
            try:
                old_session.bind.dispose()
            except Exception:
                pass

def session_commit(success=None):
    try:
        session.commit()
        if success:
            log.info(success)
    except (exc.OperationalError, exc.InvalidRequestError) as e:
        session.rollback()
        log.error(f"Commit failed: {e}")

