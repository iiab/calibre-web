import os
import re
import requests
import select
from datetime import datetime
from flask_babel import lazy_gettext as N_, gettext as _

from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS, STAT_FAIL, STAT_STARTED, STAT_WAITING
from cps.services.xb_utils import DatabaseService, Settings, execute_subprocess
from cps.xb import XKLBDB, Media
from .. import logger
from time import sleep

log = logger.create()

class TaskDownload(CalibreTask):
    """Task class for downloading media."""

    def __init__(self, task_message, media_url, original_url, current_user_name, shelf_id, duration, live_status):
        super(TaskDownload, self).__init__(task_message)
        db = XKLBDB()
        self.session = db.get_session()
        self.db_service = DatabaseService(self.session)
        self.message = task_message
        self.media_url = media_url
        self.media_url_link = f'<a href="{media_url}" target="_blank">{media_url}</a>'
        self.media_id = None
        self.original_url = original_url
        self.current_user_name = current_user_name
        self.shelf_id = shelf_id
        self.duration = datetime.utcfromtimestamp(int(duration)).strftime("%H:%M:%S") if duration else "unknown"
        self.live_status = live_status
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_WAITING
        self.progress = 0

    def run(self, worker_thread):
        """Runs the download task."""
        self.worker_thread = worker_thread
        log.info("Starting download task for URL: %s", self.media_url)
        self.start_time = datetime.now()
        self.stat = STAT_STARTED
        self.progress = 0

        lb_executable = Settings.LB_WRAPPER

        if self.media_url:
            subprocess_args = [lb_executable, "dl", self.media_url]
            log.debug("Subprocess args: %s", subprocess_args)

            # Execute the download process using process_open
            try:
                p = execute_subprocess(subprocess_args)
                self._monitor_subprocess(p)
                p.wait()
                self._post_process_download()
            except Exception as e:
                log.error("An error occurred during the subprocess execution: %s", e)
                self.message = f"{self.media_url_link} failed to download: {self.db_service.read_error_from_database(self.media_url)}"
                self.stat = STAT_FAIL
                return
            finally:
                self.end_time = datetime.now()

            if p.returncode == 0 or self.progress == 1.0:
                self.stat = STAT_FINISH_SUCCESS
                log.info("Download task for %s completed successfully.", self.media_url)
            else:
                self.stat = STAT_FAIL
                log.error("Download task for %s failed.", self.media_url)
        else:
            log.warning("No media URL provided - skipping download task.")
            self.stat = STAT_FAIL
            self.message = "No media URL provided."
            self.end_time = datetime.now()

    def _monitor_subprocess(self, process):
        """Monitors the subprocess for progress and handles timeouts."""
        log.debug("Monitoring subprocess for download progress.")
        pattern_progress = r"^downloading"
        pattern_success = re.escape(self.media_url)

        complete_progress_cycle = 0
        last_progress_time = datetime.now()
        timeout = Settings.TIMEOUT

        self.message = f"Downloading {self.media_url_link}..."
        if self.live_status == "was_live":
            self.message += f" (formerly live video, length/duration {self.duration})"

        while process.poll() is None:
            self.end_time = datetime.now()
            rlist, _, _ = select.select([process.stdout], [], [], 0.1)
            if rlist:
                line = process.stdout.readline()
                if line:
                    if re.search(pattern_success, line) or complete_progress_cycle == 4:
                        self.progress = 0.99
                        log.debug("Download progress reached 99%.")
                        break
                    elif re.search(pattern_progress, line):
                        percentage_match = re.search(r'\d+', line)
                        if percentage_match:
                            percentage = int(percentage_match.group())
                            if percentage < 100:
                                self.progress = min(0.99, (complete_progress_cycle + (percentage / 100)) / 4)
                            if percentage == 100:
                                complete_progress_cycle += 1
                                last_progress_time = datetime.now()
                                log.debug("Completed progress cycle %d.", complete_progress_cycle)
            else:
                elapsed_time = (datetime.now() - last_progress_time).total_seconds()
                if elapsed_time >= timeout:
                    self.message = f"{self.media_url_link} is taking longer than expected. It could be a stuck download due to unavailable fragments. Please wait as we keep trying."
                    log.warning("Download taking longer than expected for URL: %s", self.media_url)
            sleep(0.1)

    def _post_process_download(self):
        """Handles post-download operations."""
        log.debug("Post-processing after download.")
        try:
            with self.session.begin():
                # Fetch the media entry from the database
                media_entry = self.session.query(Media).filter(
                    Media.webpath == self.media_url,
                    ~Media.path.like('http%')
                ).first()

                if media_entry:
                    self.media_id = media_entry.id
                    requested_file = media_entry.path

                    # Abort if there is not a path
                    if not requested_file:
                        self._handle_no_path(media_entry)
                        return
                else:
                    self._handle_no_media_entry()
                    return

                self.message += "\nAlmost done..."
                response = requests.get(self.original_url, params={
                    "requested_file": requested_file,
                    "current_user_name": self.current_user_name,
                    "shelf_id": self.shelf_id,
                    "media_id": self.media_id
                })
                if response.status_code == 200:
                    log.info("Successfully sent the requested file to %s", self.original_url)
                    file_downloaded = response.json().get("file_downloaded")
                    self.message = f"Successfully downloaded {self.media_url_link} to <br><br>{file_downloaded}"
                    new_video_path = response.json().get("new_book_path")
                    if new_video_path:
                        new_video_path = next(
                            (os.path.join(new_video_path, file) for file in os.listdir(new_video_path) if file.endswith((".webm", ".mp4"))),
                            None
                        )

                        # Update media path and webpath in the database
                        media_entry.path = new_video_path
                        media_entry.webpath = f"{self.media_url}&timestamp={int(datetime.now().timestamp())}"
                        self.session.commit()
                        self.progress = 1.0
                        log.info("Media entry updated in the database.")
                    else:
                        log.error("new_book_path not found in the response")
                        self.message = f"{self.media_url_link} failed to download: 'new_book_path' not found in response"
                else:
                    log.error("Failed to send the requested file to %s", self.original_url)
                    self.message = f"{self.media_url_link} failed to download: {response.status_code} {response.reason}"

        except Exception as e:
            self.session.rollback()
            log.error("An error occurred during post-download operations: %s", e)
            self.message = f"{self.media_url_link} failed to download: {e}"
            self.stat = STAT_FAIL

    def _handle_no_path(self, media_entry):
        """Handles the case when no path is found in the media entry."""
        log.warning("No path found in the media entry for media ID: %s", media_entry.id)
        error_message = self.db_service.read_error_from_database(self.media_url)
        if error_message != "No error message found in database":
            log.error("An error occurred while trying to download %s: %s", self.media_url, error_message)
            self.message = f"{self.media_url_link} failed to download: {error_message}"
        else:
            log.error("%s failed to download: No path or error found in the database.", self.media_url)
            self.message = f"{self.media_url_link} failed to download: No path or error found in the database."

            # Delete media and captions entries
            self.db_service.delete_media_and_captions(self.media_id, self.media_url)

    def _handle_no_media_entry(self):
        """Handles the case when no media entry is found in the database."""
        log.warning("No media entry found in the database for webpath %s", self.media_url)
        error_message = self.db_service.read_error_from_database(self.media_url)
        if error_message != "No error message found in database":
            log.error("An error occurred while trying to download %s: %s", self.media_url, error_message)
            self.message = f"{self.media_url_link} failed to download: {error_message}"
        else:
            log.error("%s failed to download: No path or error found in the database.", self.media_url)
            self.message = f"{self.media_url_link} failed to download: No path or error found in the database."

            media_entry = self.session.query(Media.id).filter(Media.webpath == self.media_url).first()
            if media_entry:
                self.media_id = media_entry.id
                # Delete media and captions entries
                self.db_service.delete_media_and_captions(self.media_id, self.media_url)
            else:
                self.media_id = None

    @property
    def name(self):
        return N_("Download")

    def __str__(self):
        return f"Download task for {self.media_url}"

    @property
    def is_cancellable(self):
        return True
