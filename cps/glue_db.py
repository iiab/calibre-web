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

    def __new__(cls, mapping_db_file=None):
        if cls._instance is None:
            cls._instance = super(GlueDB, cls).__new__(cls)
            cls._instance._mapping_db_file = mapping_db_file or MAPPING_DB_FILE
            cls._instance._init_engine()
            cls._instance._init_session_factory()
            log.info("GlueDB instance created with database file: %s", cls._instance._mapping_db_file)
        return cls._instance

    def _init_engine(self):
        # Ensure database file exists, if not, create it
        if not os.path.exists(self._mapping_db_file):
            log.info(f"Creating new glue database at {self._mapping_db_file}")
            try:
                open(self._mapping_db_file, 'a').close()  # Create the empty file
            except OSError as e:
                log.error(f"Failed to create database file: {e}")
                raise

        self.engine = create_engine(
            f'sqlite:///{self._mapping_db_file}',
            echo=False,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine, checkfirst=True)

    def _init_session_factory(self):
        self.SessionFactory = scoped_session(
            sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        )
        self.session = self.SessionFactory()

    def get_session(self):
        return self.session

    def dispose(self):
        if self.session:
            self.session.close()
            self.SessionFactory.remove()
        if self.engine:
            self.engine.dispose()
        GlueDB._instance = None
        log.info("GlueDB instance disposed.")
