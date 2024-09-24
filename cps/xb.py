import os
from sqlalchemy import (
    create_engine, Column, Integer, Text, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy import exc
from sqlalchemy.sql import text

Base = declarative_base()

class Media(Base):
    __tablename__ = 'media'
    __table_args__ = (
        Index('idx_media_id', 'id'),
        Index('idx_media_time_deleted', 'time_deleted'),
        Index('idx_media_playlists_id', 'playlists_id'),
        Index('idx_media_size', 'size'),
        Index('idx_media_duration', 'duration'),
        Index('idx_media_time_created', 'time_created'),
        Index('idx_media_time_modified', 'time_modified'),
        Index('idx_media_time_downloaded', 'time_downloaded'),
        Index('idx_media_fps', 'fps'),
        Index('idx_media_view_count', 'view_count'),
        Index('idx_media_uploader', 'uploader'),
        Index('idx_media_path', 'path', unique=True),
    )

    id = Column(Integer, primary_key=True)
    time_deleted = Column(Integer)
    playlists_id = Column(Integer)
    size = Column(Integer)
    duration = Column(Integer)
    time_created = Column(Integer)
    time_modified = Column(Integer)
    time_downloaded = Column(Integer)
    fps = Column(Integer)
    view_count = Column(Integer)
    path = Column(Text)
    webpath = Column(Text)
    extractor_id = Column(Text)
    title = Column(Text)
    uploader = Column(Text)
    time_uploaded = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    live_status = Column(Text)
    type = Column(Text)
    video_codecs = Column(Text)
    audio_codecs = Column(Text)
    subtitle_codecs = Column(Text)
    other_codecs = Column(Text)
    video_count = Column(Integer)
    audio_count = Column(Integer)
    chapter_count = Column(Integer)
    other_count = Column(Integer)
    language = Column(Text)
    subtitle_count = Column(Integer)
    download_attempts = Column(Integer)
    error = Column(Text)

    captions = relationship("Caption", back_populates="media")

    def __repr__(self):
        return f"<Media(title='{self.title}', path='{self.path}')>"

class Caption(Base):
    __tablename__ = 'captions'
    __table_args__ = (
        Index('idx_captions_media_id', 'media_id'),
        Index('idx_captions_time', 'time'),
    )

    media_id = Column(Integer, ForeignKey('media.id'), primary_key=True)
    time = Column(Integer, primary_key=True)
    text = Column(Text)

    media = relationship("Media", back_populates="captions")

    def __repr__(self):
        return f"<Caption(media_id={self.media_id}, time={self.time}, text={self.text})>"

class Playlists(Base):
    __tablename__ = 'playlists'
    __table_args__ = (
        Index('idx_playlists_id', 'id'),
        Index('idx_playlists_time_modified', 'time_modified'),
        Index('idx_playlists_time_deleted', 'time_deleted'),
        Index('idx_playlists_time_created', 'time_created'),
        Index('idx_playlists_hours_update_delay', 'hours_update_delay'),
        Index('idx_playlists_uploader', 'uploader'),
        Index('idx_playlists_extractor_config', 'extractor_config'),
        Index('idx_playlists_profile', 'profile'),
        Index('idx_playlists_path', 'path', unique=True),
        Index('idx_playlists_extractor_key', 'extractor_key'),
    )

    id = Column(Integer, primary_key=True)
    time_modified = Column(Integer)
    time_deleted = Column(Integer)
    time_created = Column(Integer)
    hours_update_delay = Column(Integer)
    path = Column(Text)
    extractor_key = Column(Text)
    profile = Column(Text)
    extractor_config = Column(Text)
    extractor_playlist_id = Column(Text)
    title = Column(Text)
    uploader = Column(Text)

    def __repr__(self):
        return f"<Playlists(title='{self.title}', path='{self.path}')>"

# Initialize the SQLAlchemy engine and session
engine = None
SessionFactory = None
Session = None

def init_db(xklb_db_path):
    engine = create_engine(f'sqlite:///{xklb_db_path}', echo=False)
    SessionFactory = sessionmaker(bind=engine)
    Session = scoped_session(SessionFactory)

    if not os.path.exists(xklb_db_path):
        print(f"Database file not found at {xklb_db_path}, importing a new blank database.")
        pass
        print("New blank database imported.")
    else:
        print(f"Database file found at {xklb_db_path}.")
        # Ensure that tables, indexes, FTS tables, and triggers exist
        Base.metadata.create_all(engine)

def session_commit(session, success=None):
    try:
        session.commit()
        if success:
            print(success)
    except (exc.OperationalError, exc.InvalidRequestError) as e:
        session.rollback()
        print(f"Commit failed: {e}")
