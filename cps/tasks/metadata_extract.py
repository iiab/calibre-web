import os
import re
import requests
from datetime import datetime
from flask_babel import lazy_gettext as N_, gettext as _

from cps.services.worker import WorkerThread
from cps.tasks.download import TaskDownload
from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS, STAT_FAIL, STAT_STARTED, STAT_WAITING
from cps.services.xb_utils import (
    DatabaseService, format_media_url, format_original_url,
    Settings, execute_subprocess
)
from cps.xb import XKLBDB, Media
from sqlalchemy.orm import Session
from .. import logger

log = logger.create()

class TaskMetadataExtract(CalibreTask):
    """Task class for metadata extraction."""

    def __init__(self, task_message, media_url, original_url, current_user_name):
        super(TaskMetadataExtract, self).__init__(task_message)
        db = XKLBDB()
        self.session = db.get_session()
        self.db_service = DatabaseService(self.session)
        self.message = task_message
        self.media_url = format_media_url(media_url)
        self.media_url_link = f'<a href="{self.media_url}" target="_blank">{self.media_url}</a>'
        self.original_url = format_original_url(original_url)
        self.is_playlist = None
        self.current_user_name = current_user_name
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_WAITING
        self.progress = 0
        self.shelf_title = None
        self.shelf_id = None
        self.unavailable = []

    def _execute_subprocess(self, subprocess_args):
        """Executes a subprocess and handles its output."""
        log.debug("Executing subprocess with args: %s", subprocess_args)
        try:
            p = execute_subprocess(subprocess_args)
            while p.poll() is None:
                line = p.stdout.readline()
                if "[download] Downloading playlist:" in line:
                    self.is_playlist = True
                    self.shelf_title = line.split("Downloading playlist: ")[1].strip()
                    log.info("Detected playlist: %s", self.shelf_title)
                    break
            p.wait()
            self.message = self.media_url_link + "..."
            return p
        except Exception as e:
            self.message = f"{self.media_url_link} failed: {e}"
            return None

    def _send_shelf_title(self):
        """Sends the shelf title to the original URL."""
        log.debug("Sending shelf title to original URL.")
        try:
            response = requests.get(self.original_url, params={
                "current_user_name": self.current_user_name,
                "shelf_title": self.shelf_title
            })
            if response.status_code == 200:
                self.shelf_id = response.json()["shelf_id"]
                self.shelf_title = response.json()["shelf_title"]
                log.info("Shelf title sent successfully. Shelf ID: %s", self.shelf_id)
            else:
                log.error("Unexpected status code %s when sending shelf title.", response.status_code)
        except Exception as e:
            log.error("An error occurred during the shelf title sending: %s", e)

    def _update_metadata(self, requested_urls):
        """Updates metadata for requested URLs."""
        log.debug("Updating metadata for requested URLs.")
        failed_urls = []
        subprocess_args_list = [[Settings.LB_WRAPPER, "tubeadd", requested_url] for requested_url in requested_urls.keys()]

        for index, subprocess_args in enumerate(subprocess_args_list):
            p = self._execute_subprocess(subprocess_args)
            if p is not None:
                self.progress = (index + 1) / len(subprocess_args_list)
                log.debug("Metadata updated for URL: %s", subprocess_args[2])
            else:
                failed_urls.append(subprocess_args[2])
                log.error("Failed to update metadata for URL: %s", subprocess_args[2])
            p.wait()

        # Remove failed URLs from requested_urls
        for url in failed_urls:
            requested_urls.pop(url, None)
        log.info("Metadata update completed.")

    def _sort_and_limit_requested_urls(self, requested_urls):
        """Sorts and limits the requested URLs based on views per day."""
        log.debug("Sorting and limiting requested URLs.")
        sorted_urls = dict(sorted(requested_urls.items(), key=lambda item: item[1]["views_per_day"], reverse=True))
        limited_urls = dict(list(sorted_urls.items())[:min(Settings.MAX_VIDEOS_PER_DOWNLOAD, len(sorted_urls))])
        log.info("Requested URLs sorted and limited to %d entries.", len(limited_urls))
        return limited_urls

    def _add_download_tasks_to_worker(self, requested_urls):
        """Adds download tasks to the worker thread."""
        log.debug("Adding download tasks to the worker thread.")
        num_requested_urls = len(requested_urls)
        total_duration = 0
        for index, (requested_url, url_data) in enumerate(requested_urls.items()):
            duration = url_data["duration"]
            total_duration += duration
            live_status = url_data["live_status"]
            task_download = TaskDownload(
                _("Downloading %(url)s...", url=requested_url),
                requested_url,
                self.original_url,
                self.current_user_name,
                self.shelf_id,
                str(duration),
                live_status
            )
            WorkerThread.add(self.current_user_name, task_download)

        self.message = self.media_url_link + f"<br><br>" \
                       f"Number of Videos: {num_requested_urls}/{num_requested_urls}<br>" \
                       f"Total Duration: {datetime.utcfromtimestamp(total_duration).strftime('%H:%M:%S')}"

        if self.shelf_title:
            shelf_url = re.sub(r"/meta(?=\?|$)", r"/shelf", self.original_url) + f"/{self.shelf_id}"
            self.message += f"<br><br>Shelf Title: <a href='{shelf_url}' target='_blank'>{self.shelf_title}</a>"

        if self.unavailable:
            self.message += "<br><br>Unavailable Video(s):<br>" + "<br>".join(
                f'<a href="{url}" target="_blank">{url}</a>' for url in self.unavailable)
            upcoming_live_urls = [url for url, url_data in requested_urls.items() if url_data["live_status"] == "is_upcoming"]
            live_urls = [url for url, url_data in requested_urls.items() if url_data["live_status"] == "is_live"]
            if upcoming_live_urls:
                self.message += "<br><br>Upcoming Live Video(s):<br>" + "<br>".join(
                    f'<a href="{url}" target="_blank">{url}</a>' for url in upcoming_live_urls)
            if live_urls:
                self.message += "<br><br>Live Video(s):<br>" + "<br>".join(
                    f'<a href="{url}" target="_blank">{url}</a>' for url in live_urls)
        log.info("Download tasks added to the worker thread.")

    def run(self, worker_thread):
        """Runs the metadata extraction task."""
        self.worker_thread = worker_thread
        log.info("Starting metadata extraction task for URL: %s", self.media_url)
        self.start_time = datetime.now()
        self.stat = STAT_STARTED
        self.progress = 0

        lb_executable = Settings.LB_WRAPPER
        subprocess_args = [lb_executable, "tubeadd", self.media_url]

        p = self._execute_subprocess(subprocess_args)
        if p is None:
            self.stat = STAT_FAIL
            return

        try:
            with self.session.begin():
                # self.db_service.remove_shorts_from_db()
                requested_urls = self.db_service.fetch_requested_urls(self.unavailable)

                if not requested_urls:
                    self._handle_no_requested_urls()
                    self.stat = STAT_FAIL
                    return

                if self.is_playlist:
                    self._send_shelf_title()
                    self._update_metadata(requested_urls)
                    self.db_service.calculate_views_per_day(requested_urls)
                    requested_urls = self._sort_and_limit_requested_urls(requested_urls)
                    self.db_service.update_playlist_path(self.media_url)
                else:
                    extractor_id = self.db_service.get_extractor_id(self.media_url)
                    if extractor_id:
                        requested_urls = {url: data for url, data in requested_urls.items() if extractor_id in url}
                    else:
                        self.message = f"{self.media_url_link} failed: Extractor ID not found."
                        self.stat = STAT_FAIL
                        return

                self._add_download_tasks_to_worker(requested_urls)

            self.progress = 1.0
            self.stat = STAT_FINISH_SUCCESS
            self.end_time = datetime.now()
            log.info("Metadata extraction task for %s completed successfully.", self.media_url)

        except Exception as e:
            self.session.rollback()
            log.error("An error occurred during the metadata extraction task: %s", e)
            self.message = f"{self.media_url_link} failed: {e}"
            self.stat = STAT_FAIL

    def _handle_no_requested_urls(self):
        """Handles the case when no requested URLs are found."""
        log.debug("Handling no requested URLs.")
        if self.unavailable:
            self.message = f"{self.media_url_link} failed: Video not available."
        else:
            try:
                extractor_id = self.db_service.get_extractor_id(self.media_url)
                if extractor_id:
                    media_entry = self.session.query(Media).filter(
                        Media.extractor_id == extractor_id,
                        Media.webpath == self.media_url
                    ).first()
                    if media_entry and media_entry.error:
                        error_message = media_entry.error
                        self.message = f"{self.media_url_link} failed previously with this error: {error_message}<br><br>To force a retry, submit the URL again."
                        media_id = media_entry.id
                        # Delete media and captions entries
                        self.db_service.delete_media_and_captions(media_id, self.media_url)
                    else:
                        self.message = f"{self.media_url_link} failed: An error occurred while trying to fetch the requested URLs."
                else:
                    self.message = f"{self.media_url_link} failed: Extractor ID not found."
            except Exception as e:
                log.error("Error while checking error message: %s", e)
                self.message = f"{self.media_url_link} failed: An error occurred while checking the error message."

    @property
    def name(self):
        return N_("Metadata Fetch")

    def __str__(self):
        return f"Metadata fetch task for {self.media_url}"

    @property
    def is_cancellable(self):
        return True
