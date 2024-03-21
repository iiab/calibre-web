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
        self.media_url = media_url
        self.media_url_link = f'<a href="{media_url}" target="_blank">{media_url}</a>'
        # (?=...) is a "lookahead assertion" https://docs.python.org/3/library/re.html#regular-expression-syntax
        self.original_url = re.sub(r"/media(?=\?|$)", r"/meta", original_url)
        self.current_user_name = current_user_name
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_WAITING
        self.progress = 0
        self.columns = None
        self.shelf_title = None
        self.shelf_id = None
        self.main_message = None

    def run(self, worker_thread):
        """Run the metadata fetching task"""
        self.worker_thread = worker_thread
        log.info("Starting to fetch metadata for URL: %s", self.media_url)
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_STARTED
        self.progress = 0

        lb_executable = os.getenv("LB_WRAPPER", "lb-wrapper")

        if self.media_url:
            if "&" in self.media_url:
                self.media_url = self.media_url.split("&")[0]
            subprocess_args = [lb_executable, "tubeadd", self.media_url]
            log.info("Subprocess args: %s", subprocess_args)

            # Execute the metadata fetching process using process_open
            try:
                p = process_open(subprocess_args, newlines=True)
                p.wait()
                self_main_message = f"{self.media_url_link}"
                self.message = self_main_message + "..."

                # Database operations
                requested_urls = {}
                with sqlite3.connect(XKLB_DB_FILE) as conn:
                    try:
                        cursor = conn.execute("PRAGMA table_info(media)")
                        self.columns = [column[1] for column in cursor.fetchall()]
                        if "error" in self.columns:
                            rows = conn.execute("SELECT path, duration, time_uploaded, view_count, size FROM media WHERE error IS NULL AND path LIKE 'http%'").fetchall()
                        else:
                            rows = conn.execute("SELECT path, duration, time_uploaded, view_count, size FROM media WHERE path LIKE 'http%'").fetchall()

                        if not rows:
                            log.info("No urls found in the database")
                            error = conn.execute("SELECT error, webpath FROM media WHERE error IS NOT NULL AND webpath = ?", (self.media_url,)).fetchone()
                            if error:
                                log.error("[xklb] An error occurred while trying to retrieve the data for %s: %s", error[1], error[0])
                                self.progress = 0
                                self.message = f"{error[1]} gave no data : {error[0]}"
                            return

                        for row in rows:
                            path = row[0]
                            duration = row[1]
                            time_uploaded = row[2]
                            view_count = row[3]
                            size = row[4]

                            time_uploaded = datetime.utcfromtimestamp(time_uploaded)
                            now = datetime.now()
                            days_since_publish = (now - time_uploaded).days or 1
                            views_per_day = view_count / days_since_publish

                            is_playlist_video = False
                            if "playlists_id" in self.columns:
                                playlist_id = conn.execute("SELECT playlists_id FROM media WHERE path = ?", (path,)).fetchone()
                                if playlist_id:
                                    is_playlist_video = True 
      
                            requested_urls[path] = {
                                "duration": duration,
                                "time_uploaded": time_uploaded,
                                "view_count": view_count,
                                "size": size,
                                "views_per_day": views_per_day,
                                "is_playlist_video": is_playlist_video
                            }

                    except sqlite3.Error as db_error:
                        log.error("An error occurred while trying to connect to the database: %s", db_error)
                        self.message = f"{self.media_url_link} failed: {db_error}"

                    # get the shelf title
                    if "list=" in self.media_url or "@" in self.media_url or any([requested_urls[url]["is_playlist_video"] for url in requested_urls.keys()]):
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
                        response = requests.get(self.original_url, params={"current_user_name": self.current_user_name, "shelf_title": self.shelf_title})
                        if response.status_code == 200:
                            self.shelf_id = response.json()["shelf_id"]
                        else:
                            log.error("An error occurred while trying to send the shelf title to %s", self.original_url)
                            
                        # remove shorts from the requested_urls dict
                        requested_urls = {url: requested_urls[url] for url in requested_urls.keys() if "shorts" not in url}

                        # sort the videos by views per day and get the top ones (up to the maximum number of videos per download or the length of the dictionary)
                        requested_urls = dict(sorted(requested_urls.items(), key=lambda item: item[1]["views_per_day"], reverse=True)[:min(MAX_VIDEOS_PER_DOWNLOAD, len(requested_urls))])
                        log.debug("Videos sorted by views per day: \n%s", "\n".join([f"{index + 1}-{conn.execute('SELECT title FROM media WHERE path = ?', (requested_url,)).fetchone()[0]}:{requested_urls[requested_url]['views_per_day']}" for index, requested_url in enumerate(requested_urls.keys())]))
                    else:
                        try:
                            extractor_id = conn.execute("SELECT extractor_id FROM media WHERE ? LIKE '%' || extractor_id || '%'", (self.media_url,)).fetchone()[0]
                            requested_urls = {url: requested_urls[url] for url in requested_urls.keys() if extractor_id in url} # filter the requested_urls dict
                        except sqlite3.Error as db_error:
                            log.error("An error occurred while trying to connect to the database: %s", db_error)
                            self.message = f"{self.media_url_link} failed to download: {db_error}"    

                conn.close()

                num_requested_urls = len(requested_urls.keys())
                total_duration = 0

                for index, requested_url in enumerate(requested_urls.keys()):
                    task_download = TaskDownload(_("Downloading %(url)s...", url=requested_url),
                                                 requested_url, self.original_url,
                                                 self.current_user_name, self.shelf_id
                                                    )
                    WorkerThread.add(self.current_user_name, task_download)

                    if requested_urls[requested_url]["duration"] is not None:
                        total_duration += requested_urls[requested_url]["duration"]
                    self.message = self_main_message + f"<br><br>Number of Videos: {index + 1}/{num_requested_urls}<br>Total Duration: {datetime.utcfromtimestamp(total_duration).strftime('%H:%M:%S')}"
                    self.progress = (index + 1) / num_requested_urls

                self.end_time = datetime.now()

            except Exception as e:
                log.error("An error occurred during the subprocess execution: %s", e)
                self.message = f"{self.media_url_link} failed: {e}"
                self.end_time = datetime.now()

            finally:
                if p.returncode == 0 or self.progress == 1.0:
                    self.stat = STAT_FINISH_SUCCESS
                else:
                    self.stat = STAT_FAIL

        else:
            log.info("No media URL provided - skipping download task")

    @property
    def name(self):
        return N_("Metadata Fetch")

    def __str__(self):
        return f"Metadata fetch task for {self.media_url}"

    @property
    def is_cancellable(self):
        return True  # Change to True if the download task should be cancellable
