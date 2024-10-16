import os
import re
from copy import deepcopy
from datetime import datetime
from itertools import groupby
from sqlalchemy.orm import Session
from sqlalchemy import literal
from cps.xb import XKLBDB, Media, Caption, Playlists
from cps.glue_db import GlueDB, MediaBooksMapping
from cps.subproc_wrapper import process_open
from cps import logger

log = logger.create()

class Settings:
    LB_WRAPPER = os.getenv('LB_WRAPPER', 'lb-wrapper')
    TIMEOUT = 120  # seconds
    MAX_VIDEOS_PER_DOWNLOAD = 10

def format_media_url(media_url):
    """Formats the media URL by removing query parameters."""
    return media_url.split("&")[0] if "&" in media_url else media_url

def format_original_url(original_url):
    """Formats the original URL to point to the metadata endpoint."""
    return re.sub(r"/media(?=\?|$)", r"/meta", original_url)

def execute_subprocess(subprocess_args):
    """Executes a subprocess and returns the process handle."""
    try:
        p = process_open(subprocess_args, newlines=True)
        return p
    except Exception as e:
        log.error("An error occurred during subprocess execution: %s", e)
        raise

class DatabaseService:
    """Service class for database operations."""

    def __init__(self, session: Session):
        db = XKLBDB()
        self.session = db.get_session()

    def remove_shorts_from_db(self):
        """Deletes media entries where the path contains 'shorts'."""
        log.debug("Removing shorts from the database.")
        try:
            self.session.query(Media).filter(Media.path.like('%shorts%')).delete(synchronize_session=False)
            self.session.commit()
            log.info("Shorts removed from the database.")
        except Exception as e:
            self.session.rollback()
            log.error("An error occurred while removing shorts from the database: %s", e)
            raise

    def fetch_requested_urls(self, unavailable: list):
        """Fetches requested URLs from the database."""
        log.debug("Fetching requested URLs from the database.")
        try:
            query = self.session.query(Media.path, Media.duration, Media.live_status)\
                .filter(Media.path.like('http%'))\
                .filter((Media.error == None) | (Media.error == ''))
            rows = query.all()
            requested_urls = {}
            for path, duration, live_status in rows:
                if duration is not None and duration > 0:
                    requested_urls[path] = {"duration": duration, "live_status": live_status}
                else:
                    unavailable.append(path)
            log.info("Fetched %d requested URLs.", len(requested_urls))
            return requested_urls
        except Exception as e:
            log.error("An error occurred while fetching requested URLs: %s", e)
            raise

    def calculate_views_per_day(self, requested_urls: dict):
        """Calculates views per day for each requested URL."""
        log.debug("Calculating views per day for requested URLs.")
        now = datetime.now()
        for requested_url in list(requested_urls.keys()):
            try:
                media_entry = self.session.query(Media).filter(Media.path == requested_url).first()
                if media_entry and media_entry.view_count and media_entry.time_uploaded:
                    view_count = media_entry.view_count
                    time_uploaded = datetime.utcfromtimestamp(media_entry.time_uploaded)
                    days_since_publish = (now - time_uploaded).days or 1
                    requested_urls[requested_url]["views_per_day"] = view_count / days_since_publish
                else:
                    # If data is missing, remove the URL from requested_urls
                    requested_urls.pop(requested_url)
                    log.warning("Removed URL %s due to missing data.", requested_url)
            except Exception as e:
                log.error("An error occurred during calculation for %s: %s", requested_url, e)
                requested_urls.pop(requested_url)
        log.info("Views per day calculated for requested URLs.")

    def update_playlist_path(self, media_url):
        """Updates the playlist path with a timestamp."""
        log.debug("Updating playlist path for URL: %s", media_url)
        try:
            playlist = self.session.query(Playlists).filter(Playlists.path == media_url).first()
            if playlist:
                playlist.path = f"{media_url}&timestamp={int(datetime.now().timestamp())}"
                self.session.commit()
                log.info("Playlist path updated for %s.", media_url)
            else:
                log.error("No playlist found with path %s", media_url)
        except Exception as e:
            self.session.rollback()
            log.error("An error occurred while updating the playlist path: %s", e)
            raise

    def get_extractor_id(self, media_url):
        """Gets the extractor ID for the given media URL."""
        log.debug("Getting extractor ID for URL: %s", media_url)
        try:
            media_entry = self.session.query(Media).filter(
                literal(media_url).like('%' + Media.extractor_id + '%')
            ).first()
            if media_entry:
                log.info("Extractor ID found: %s", media_entry.extractor_id)
                return media_entry.extractor_id
            else:
                log.error("Extractor ID not found for URL: %s", media_url)
                return None
        except Exception as e:
            log.error("An error occurred while getting extractor ID: %s", e)
            raise

    def read_error_from_database(self, media_url):
        """Reads the error message from the database."""
        log.debug("Reading error message from the database for URL: %s", media_url)
        try:
            error_entry = self.session.query(Media.error).filter(Media.webpath == media_url).first()
            if error_entry and error_entry.error:
                return error_entry.error
            else:
                return "No error message found in database"
        except Exception as e:
            log.error("An error occurred while reading error from the database: %s", e)
            return f"An error occurred while reading error from the database: {e}"

    def delete_media_and_captions(self, media_id, media_url):
        """Deletes media and captions entries for a given media ID."""
        log.debug("Deleting media and captions entries for media ID: %s", media_id)
        try:
            self.session.query(Caption).filter(Caption.media_id == media_id).delete(synchronize_session=False)
            self.session.query(Media).filter(Media.webpath == media_url).delete(synchronize_session=False)
            self.session.commit()
            log.info("Deleted media and caption entries for media ID: %s", media_id)
        except Exception as e:
            self.session.rollback()
            log.error("An error occurred while deleting media and captions: %s", e)
            raise

class MappingService:
    """Service class for mapping operations."""
    def __init__(self):
        db = GlueDB()
        self.session = db.get_session()

    def add_book_media_mapping(self, media_id, book_id):
        """Adds a mapping between the media_id and the book_id."""
        try:
            mapping = MediaBooksMapping(media_id=media_id, book_id=book_id)
            # to avoid duplicate entries, use the merge method
            self.session.merge(mapping)
            self.session.commit()
            log.info("Mapping added: %s", mapping)
        except Exception as e:
            self.session.rollback()
            log.error("An error occurred while adding mapping: %s", e)
            raise

    def get_mapping(self, media_id):
        """Gets the mapping for the given media_id."""
        try:
            mapping = self.session.query(MediaBooksMapping).filter(MediaBooksMapping.media_id == media_id).first()
            if mapping:
                log.info("Mapping found: %s", mapping)
                return mapping
            else:
                log.error("No mapping found for media ID: %s", media_id)
                return None
        except Exception as e:
            log.error("An error occurred while getting mapping: %s", e)
            raise

    def update_mapping(self, media_id, book_id):
        """Updates the mapping for the given media_id."""
        try:
            mapping = self.session.query(MediaBooksMapping).filter(MediaBooksMapping.media_id == media_id).first()
            if mapping:
                mapping.book_id = book_id
                self.session.commit()
                log.info("Mapping updated: %s", mapping)
            else:
                log.error("No mapping found for media ID: %s", media_id)
        except Exception as e:
            self.session.rollback()
            log.error("An error occurred while updating mapping: %s", e)
            raise

class CaptionSearcher:
    def __init__(self):
        self.xklb_session = XKLBDB().get_session()
        self.glue_session = GlueDB().get_session()

    def _query_database(self, term):
        """Executes a query on the xklb database and retrieves book_ids from iiab-glue.db."""
        captions = self.xklb_session.query(
            # Caption.rowid,
            Caption.media_id,
            Caption.text,
            Caption.time
        ).filter(Caption.text.like(f'%{term}%')).all()

        media_ids = [caption[0] for caption in captions]

        # Get corresponding book_ids from the glue database
        mappings = self.glue_session.query(MediaBooksMapping).filter(
            MediaBooksMapping.media_id.in_(media_ids)
        ).all()
        media_id_to_book_id = {mapping.media_id: mapping.book_id for mapping in mappings}

        # Combine captions with book_ids
        captions_list = []
        for caption in captions:
            media_id = caption[0]
            book_id = media_id_to_book_id.get(media_id)
            if book_id:
                captions_list.append({
                    'book_id': book_id,
                    'text': caption[1],
                    'time': caption[2]
                })

        return captions_list

    def _merge_captions(self, captions):
        """Merges overlapping captions for the same book_id."""
        def get_end(caption):
            return caption["time"] + (len(caption["text"]) / 4.2 / 220 * 60)

        merged_captions = []
        for book_id, group in groupby(captions, key=lambda x: x["book_id"]):
            group = list(group)
            merged_group = deepcopy(group[0])
            merged_group["end"] = get_end(group[0])
            for i in range(1, len(group)):
                if group[i]["time"] <= merged_group["end"]:
                    merged_group["text"] += " " + group[i]["text"]
                    merged_group["end"] = get_end(group[i])
                else:
                    merged_captions.append(merged_group)
                    merged_group = deepcopy(group[i])
                    merged_group["end"] = get_end(group[i])
            merged_captions.append(merged_group)

        return merged_captions

    def get_captions_search_results(self, term):
        """Searches for captions matching the term and returns book_ids."""
        captions = self._query_database(term)
        if not captions:
            return []

        merged_captions = self._merge_captions(captions)
        book_ids = list({caption['book_id'] for caption in merged_captions})

        return book_ids
