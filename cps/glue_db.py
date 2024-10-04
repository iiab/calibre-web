import os
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from . import logger

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

    def __new__(cls, glue_db_path=None):
        if cls._instance is None:
            cls._instance = super(GlueDB, cls).__new__(cls)
            cls._instance.glue_db_path = glue_db_path or os.getenv('GLUE_DB_FILE', 'iiab-glue.db') # to be determined / constants.py is a good candidate
            cls._instance._init_engine()
            cls._instance._init_session_factory()
            cls._instance.session = cls._instance.SessionFactory()
            log.info("GlueDB instance created with database file: %s", cls._instance.glue_db_path)
        return cls._instance

    def _init_engine(self):
        if not os.path.exists(self.glue_db_path):
            log.info(f"Creating new glue database at {self.glue_db_path}.")
            open(self.glue_db_path, 'a').close()
        self.engine = create_engine(
            f'sqlite:///{self.glue_db_path}',
            echo=False,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)

    def _init_session_factory(self):
        self.SessionFactory = scoped_session(sessionmaker(bind=self.engine, autocommit=False, autoflush=True))
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

