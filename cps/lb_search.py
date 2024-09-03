import sqlite3
from copy import deepcopy
from itertools import groupby

class CaptionSearcher:
    def __init__(self, db_file):
        self.db_file = db_file

    def _query_database(self, query, params=()):
        """Executes a query on the database and returns the results."""
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            return [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

    def _merge_captions(self, captions):
        """Merges overlapping captions for the same video path."""
        def get_end(caption):
            return caption["time"] + (len(caption["text"]) / 4.2 / 220 * 60)

        merged_captions = []
        for path, group in groupby(captions, key=lambda x: x["path"]):
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

    def _construct_captions_search_query(self, term):
        """Constructs the SQL query to search for captions containing the search term."""
        query = f"""
            SELECT media.path, media.title, captions.text, captions.time
            FROM captions
            JOIN media ON media.id = captions.media_id
            WHERE captions.text LIKE ?
            ORDER BY media.path, captions.time
        """
        return query, (f"%{term}%",)

    def get_search_terms(self, term):
        """Searches for captions matching the term and processes the results."""
        query, params = self._construct_captions_search_query(term)
        captions = self._query_database(query, params)
        if not captions:
            return []
        
        merged_captions = self._merge_captions(captions)
        titles = list({caption['title'] for caption in merged_captions})
        
        return titles
