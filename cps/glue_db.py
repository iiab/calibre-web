import os
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from . import logger
from .constants import MAPPING_DB_FILE

log = logger.create()
Base = declarative_base()

class MediaBooksMapping(Base):
    __tablename__ = 'media_books_mapping'
    media_id = Column(Integer, primary_key=True)
    book_id = Column(Integer, primary_key=True)

    def __repr__(self):
        return f"<MediaBooksMapping(media_id={self.media_id}, book_id={self.book_id})>"

class GlueDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlueDB, cls).__new__(cls)
            cls._instance._init_engine()
            cls._instance._init_session_factory()
            cls._instance.session = cls._instance.SessionFactory()
            log.info("GlueDB instance created with database file: %s", MAPPING_DB_FILE)
        return cls._instance

    def _init_engine(self):
        self.engine = create_engine(
            f'sqlite:///{MAPPING_DB_FILE}',
            echo=False,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool
        )
        if not os.path.exists(MAPPING_DB_FILE):
            log.info(f"Creating new glue database at {MAPPING_DB_FILE}")        
            # Create all tables defined by Base's subclasses (MediaBooksMapping)
            Base.metadata.create_all(self.engine, checkfirst=True)

    def _init_session_factory(self):
        self.SessionFactory = scoped_session(
            sessionmaker(bind=self.engine, autocommit=False, autoflush=True)
        )

    def remove_session(self):
        self.SessionFactory.remove()
    
    def get_session(self):
        return self.SessionFactory()

    def dispose(self):
        self.SessionFactory.remove()
        if self.engine:
            self.engine.dispose()
        GlueDB._instance = None
        log.info("GlueDB instance disposed.")
