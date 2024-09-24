import os
import re
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import literal
from cps.xb import Media, Caption, Playlists
from cps.subproc_wrapper import process_open

log = logging.getLogger(__name__)

class Settings:
    LB_WRAPPER = os.getenv('LB_WRAPPER', 'lb-wrapper')
    TIMEOUT = 120  # seconds
    MAX_VIDEOS_PER_DOWNLOAD = 10  # Will use constants.py for this later

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
        self.session = session

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
