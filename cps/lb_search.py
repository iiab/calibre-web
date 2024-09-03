import sqlite3
from copy import deepcopy
from itertools import groupby
from .constants import XKLB_DB_FILE

def query_database(query, params=()):
    """Executes a query on the database and returns the results."""
    with sqlite3.connect(XKLB_DB_FILE) as connection:
        cursor = connection.cursor()
        cursor.execute(query, params)
        return [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

def find_none_keys(list_of_dicts, keep_0=True):
    """Identifies keys with only None or empty values in a list of dictionaries."""
    if not list_of_dicts:
        return []

    keys = list_of_dicts[0].keys()
    return [
        key for key in keys
        if all(d.get(key) is None or (not keep_0 and d.get(key) == 0) for d in list_of_dicts)
    ]

def list_dict_filter_bool(media, keep_0=True):
    """Removes dictionary keys that have only None values across all dictionaries in the list."""
    keys_to_remove = find_none_keys(media, keep_0)
    return [
        {k: v for k, v in m.items() if k not in keys_to_remove}
        for m in media if any(m.get(k) for k in m if k not in keys_to_remove)
    ]

def merge_captions(captions):
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

def construct_captions_search_query(term):
    """Constructs the SQL query to search for captions containing the search term."""
    query = f"""
        SELECT media.path, media.title, captions.text, captions.time
        FROM captions
        JOIN media ON media.id = captions.media_id
        WHERE captions.text LIKE ?
        ORDER BY media.path, captions.time
    """
    return query, (f"%{term}%",)

def get_search_terms(term):
    """Searches for captions matching the term and processes the results."""
    query, params = construct_captions_search_query(term)
    captions = query_database(query, params)
    if not captions:
        return []
    
    merged_captions = merge_captions(captions)
    titles = list({caption['title'] for caption in merged_captions})
    
    return titles
