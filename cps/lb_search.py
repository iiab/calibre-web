import os
import re

from . import logger
from .constants import XKLB_DB_FILE
from .subproc_wrapper import process_open

log = logger.create()

def get_search_terms(term):
    """Perform a search against xklb-metadata.db"""
    video_titles = []
    lb_executable = os.getenv("LB_WRAPPER", "lb-wrapper")

    if term:
        subprocess_args = [lb_executable, "search", term]
        log.debug("Executing: %s", subprocess_args)

        try:
            p = process_open(subprocess_args, newlines=True)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                log.error("Error executing lb-wrapper: %s", stderr)
                return video_titles
            pattern = r"^[^\d\n].*?(?= - )"
            matches = re.findall(pattern, stdout, re.MULTILINE)
            video_titles.extend(matches)
        except Exception as ex:
            log.error("Error executing lb-wrapper: %s", ex)

    return video_titles
