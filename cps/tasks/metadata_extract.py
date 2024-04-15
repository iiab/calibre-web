import os
import re
import requests
import sqlite3
from datetime import datetime
from flask_babel import lazy_gettext as N_, gettext as _

from cps.constants import XKLB_DB_FILE, MAX_VIDEOS_PER_DOWNLOAD
from cps.services.worker import WorkerThread
from cps.tasks.download import TaskDownload
from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS, STAT_FAIL, STAT_STARTED, STAT_WAITING
from cps.subproc_wrapper import process_open
from .. import logger

log = logger.create()

class TaskMetadataExtract(CalibreTask):
    def __init__(self, task_message, media_url, original_url, current_user_name):
        super(TaskMetadataExtract, self).__init__(task_message)
        self.message = task_message
        self.media_url = self._format_media_url(media_url)
        self.media_url_link = f'<a href="{self.media_url}" target="_blank">{self.media_url}</a>'
        self.original_url = self._format_original_url(original_url)
        self.type_of_url = self._get_type_of_url(self.media_url)
        self.current_user_name = current_user_name
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_WAITING
        self.progress = 0
        self.columns = None
        self.shelf_title = None
        self.shelf_id = None

    def _format_media_url(self, media_url):
        return media_url.split("&")[0] if "&" in media_url else media_url

    def _format_original_url(self, original_url):
        # (?=...) is a "lookahead assertion" https://docs.python.org/3/library/re.html#regular-expression-syntax
        return re.sub(r"/media(?=\?|$)", r"/meta", original_url)

    def _get_type_of_url(self, media_url):
        if "list=" in media_url:
            return "playlist"
        elif "@" in media_url:
            return "channel"
        else:
            return "video"

    def _execute_subprocess(self, subprocess_args):
        try:
            p = process_open(subprocess_args, newlines=True)
            p.wait()
            self.message = self.media_url_link + "..."
            return p
        except Exception as e:
            log.error("An error occurred during subprocess execution: %s", e)
            self.message = f"{self.media_url_link} failed: {e}"
            return None

    def _fetch_requested_urls(self, conn):
        try:
            cursor = conn.execute("PRAGMA table_info(media)")
            self.columns = [column[1] for column in cursor.fetchall()]
            query = ("SELECT path, duration FROM media WHERE error IS NULL AND path LIKE 'http%'"
                     if "error" in self.columns
                     else "SELECT path, duration FROM media WHERE path LIKE 'http%'")
            rows = conn.execute(query).fetchall()
            return {row[0]: {"duration": row[1], "is_playlist_video": self._is_playlist_video(row[0], conn)} for row in rows}
        except sqlite3.Error as db_error:
            log.error("An error occurred while trying to connect to the database: %s", db_error)
            self.message = f"{self.media_url_link} failed: {db_error}"
            return {}

    def _is_playlist_video(self, path, conn):
        try:
            return bool(conn.execute("SELECT playlists_id FROM media WHERE path = ?", (path,)).fetchone())
        except sqlite3.Error as db_error:
            log.error("An error occurred while trying to connect to the database: %s", db_error)
            return False

    def _get_shelf_title(self, conn):
        url_part = self.media_url.split("/")[-1]
        if "list=" in url_part:
            url_part = url_part.split("list=")[-1]
            try:
                self.shelf_title = conn.execute("SELECT title FROM playlists WHERE extractor_playlist_id = ?", (url_part,)).fetchone()[0]
            except sqlite3.Error as db_error:
                log.error("An error occurred while trying to connect to the database: %s", db_error)
        elif "@" in url_part:
            self.shelf_title = url_part.split("@")[-1]
        else:
            self.shelf_title = "Unnamed Bookshelf"

    def _send_shelf_title(self):
        try:
            response = requests.get(self.original_url, params={"current_user_name": self.current_user_name, "shelf_title": self.shelf_title})
            if response.status_code == 200:
                self.shelf_id = response.json()["shelf_id"]
            else:
                log.error("Received unexpected status code %s while sending the shelf title to %s", response.status_code, self.original_url)
        except Exception as e:
            log.error("An error occurred during the shelf title sending: %s", e)

    def _update_metadata(self, requested_urls):
        failed_urls = []
        subprocess_args_list = [[os.getenv("LB_WRAPPER", "lb-wrapper"), "tubeadd", requested_url] for requested_url in requested_urls.keys()]
        
        for index, subprocess_args in enumerate(subprocess_args_list):
            try:
                p = self._execute_subprocess(subprocess_args)
                if p is not None:
                    self.progress = (index + 1) / len(subprocess_args_list)
                else:
                    failed_urls.append(subprocess_args[2])
                p.wait()    
            except Exception as e:
                log.error("An error occurred during updating the metadata of %s: %s", subprocess_args[2], e)
                self.message = f"{subprocess_args[2]} failed: {e}"
                failed_urls.append(subprocess_args[2])

        requested_urls = {url: requested_urls[url] for url in requested_urls.keys() if "shorts" not in url and url not in failed_urls}

    def _calculate_views_per_day(self, requested_urls, conn):
        now = datetime.now()
        for requested_url in requested_urls.keys():
            try:
                view_count = conn.execute("SELECT view_count FROM media WHERE path = ?", (requested_url,)).fetchone()[0]
                time_uploaded = datetime.utcfromtimestamp(conn.execute("SELECT time_uploaded FROM media WHERE path = ?", (requested_url,)).fetchone()[0])
                days_since_publish = (now - time_uploaded).days or 1
                requested_urls[requested_url]["views_per_day"] = view_count / days_since_publish
            except Exception as e:
                log.error("An error occurred during the calculation of views per day for %s: %s", requested_url, e)
                self.message = f"{requested_url} failed: {e}"

    def _sort_and_limit_requested_urls(self, requested_urls):
        return dict(sorted(requested_urls.items(), key=lambda item: item[1]["views_per_day"], reverse=True)[:min(MAX_VIDEOS_PER_DOWNLOAD, len(requested_urls))])

    def _add_download_tasks_to_worker(self, requested_urls):
        for index, requested_url in enumerate(requested_urls.keys()):
            task_download = TaskDownload(_("Downloading %(url)s...", url=requested_url),
                                         requested_url, self.original_url,
                                         self.current_user_name, self.shelf_id)
            WorkerThread.add(self.current_user_name, task_download)
            num_requested_urls = len(requested_urls)
            total_duration = sum(url_data["duration"] for url_data in requested_urls.values())
            self.message = self.media_url_link + f"<br><br>Number of Videos: {index + 1}/{num_requested_urls}<br>Total Duration: {datetime.utcfromtimestamp(total_duration).strftime('%H:%M:%S')}"

    def run(self, worker_thread):
        self.worker_thread = worker_thread
        log.info("Starting to fetch metadata for URL: %s", self.media_url)
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_STARTED
        self.progress = 0

        lb_executable = os.getenv("LB_WRAPPER", "lb-wrapper")
        subprocess_args = [lb_executable, "tubeadd", self.media_url]

        p = self._execute_subprocess(subprocess_args)
        if p is None:
            self.stat = STAT_FAIL
            return

        with sqlite3.connect(XKLB_DB_FILE) as conn:
            requested_urls = self._fetch_requested_urls(conn)
            if not requested_urls:
                return

            if self.type_of_url != "video":
                self._get_shelf_title(conn)
                if any([requested_urls[url]["is_playlist_video"] for url in requested_urls.keys()]):
                    self._send_shelf_title()
                self._update_metadata(requested_urls)
                self._calculate_views_per_day(requested_urls, conn)
                requested_urls = self._sort_and_limit_requested_urls(requested_urls)
            else:
                try:
                    extractor_id = conn.execute("SELECT extractor_id FROM media WHERE ? LIKE '%' || extractor_id || '%'", (self.media_url,)).fetchone()[0]
                    requested_urls = {url: requested_urls[url] for url in requested_urls.keys() if extractor_id in url}
                except Exception as e:
                    log.error("An error occurred during the selection of the extractor ID: %s", e)
                    self.message = f"{self.media_url_link} failed: {e}"
                    return

            self._add_download_tasks_to_worker(requested_urls)
        conn.close()

        self.stat = STAT_FINISH_SUCCESS

    @property
    def name(self):
        return N_("Metadata Fetch")

    def __str__(self):
        return f"Metadata fetch task for {self.media_url}"

    @property
    def is_cancellable(self):
        return True  # Change to True if the download task should be cancellable
