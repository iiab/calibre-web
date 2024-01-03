import os
import requests
import sqlite3
import subprocess
import re
from datetime import datetime
from flask import flash
from flask_babel import lazy_gettext as N_
from cps.constants import SURVEY_DB_FILE
from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS, STAT_FAIL, STAT_STARTED, STAT_WAITING
from .. import logger

log = logger.create()

class TaskDownload(CalibreTask):
    def __init__(self, task_message, media_url, original_url, current_user_name):
        super(TaskDownload, self).__init__(task_message)
        self.message = task_message
        self.media_url = media_url
        self.original_url = original_url
        self.current_user_name = current_user_name
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_WAITING
        self.progress = 0

    def run(self, worker_thread):
        """Run the download task."""
        self.worker_thread = worker_thread
        log.info("Starting download task for URL: %s", self.media_url)
        self.start_time = datetime.now()
        self.stat = STAT_STARTED
        self.progress = 0

        lb_executable = os.getenv("LB_WRAPPER", "lb-wrapper")

        if self.media_url:
            subprocess_args = [lb_executable, self.media_url]
            log.info("Subprocess args: %s", subprocess_args)

            try:
                p = subprocess.Popen(subprocess_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

                for line in p.stdout:
                    log.info(line.strip())

                    # Check if the line contains progress information
                    match = re.search(r'\[download\]:\s+(\d+\.\d)%', line)
                    if match:
                        percentage = float(match.group(1))
                        self.progress = percentage / 100.0

                p.communicate()  # Wait for the process to complete

                self.progress = 1.0

                # Database operations
                requested_files = []
                with sqlite3.connect(SURVEY_DB_FILE) as conn:
                    try:
                        # Get the requested files from the database
                        requested_files = list(set([row[0] for row in conn.execute("SELECT path FROM media").fetchall() if not row[0].startswith("http")]))
                        log.info("Requested files: %s", requested_files)

                        # Abort if there are no requested files
                        if not requested_files:
                            log.info("No requested files found in the database")
                            # Log the error found in the database
                            error = conn.execute("SELECT error, webpath FROM media WHERE error IS NOT NULL").fetchone()
                            if error:
                                log.error("[xklb] An error occurred while trying to download %s: %s", error[1], error[0])
                                self.progress = 0
                            return
                    except sqlite3.Error as db_error:
                        log.error("An error occurred while trying to connect to the database: %s", db_error)
                    
                    # get the shelf title if it exists
                    try:
                        shelf_title = conn.execute("SELECT title FROM playlists").fetchone()[0]                                
                    except sqlite3.Error as db_error:
                        if "no such table: playlists" in str(db_error):
                            log.info("No playlists table found in the database")
                        else:
                            log.error("An error occurred while trying to connect to the database: %s", db_error)
                    finally:
                        shelf_title = None

                conn.close() 

                response = requests.get(self.original_url, params={"requested_files": requested_files, "current_user_name": self.current_user_name, "shelf_title": shelf_title})
                if response.status_code == 200:
                    log.info("Successfully sent the list of requested files to %s", self.original_url)
                else:
                    log.error("Failed to send the list of requested files to %s", self.original_url)
                    self.progress = 0
            
            except subprocess.CalledProcessError as e:
                log.error("An error occurred during the subprocess execution: %s", e)
                flash("Failed to complete the download process", category="error")

            finally:
                if p.returncode == 0 and self.progress == 1.0:
                    self.stat = STAT_FINISH_SUCCESS
                else:
                    self.stat = STAT_FAIL

        else:
            log.info("No media URL provided - skipping download task")

    @property
    def name(self):
        return N_("Download")

    def __str__(self):
        return f"Download {self.media_url}"

    @property
    def is_cancellable(self):
        return True  # Change to True if the download task should be cancellable
