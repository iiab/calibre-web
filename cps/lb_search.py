import os
import sqlite3
import itertools
from . import logger
from .constants import XKLB_DB_FILE

log = logger.create()

class CaptionSearcher:
    def __init__(self, db_file):
        self.db_file = db_file

    def _connect(self):
        return sqlite3.connect(self.db_file)

    def _detect_fts(self, conn, table_name):
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            log.error("Failed to detect FTS for table %s: %s", table_name, e)
            return None

    def _get_columns(self, conn, table_name):
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            return {col[1]: col[2] for col in cursor.fetchall()}
        except sqlite3.Error as e:
            log.error("Failed to get columns for table %s: %s", table_name, e)
            return {}

    def _construct_search_bindings(self, include, exclude, columns, exact=False, flexible_search=False):
        param_key = f"S_{os.urandom(4).hex()}"
        bindings = {}

        includes_sql = " OR ".join(f"{col} LIKE :{param_key}include{idx}" for idx, col in enumerate(columns))
        if includes_sql:
            bindings.update({
                f"{param_key}include{idx}": f"%{inc.replace(' ', '%').replace('%%', ' ')}%"
                for idx, inc in enumerate(include)
            })

        excludes_sql = " AND ".join(f"COALESCE({col},'') NOT LIKE :{param_key}exclude{idx}" for idx, col in enumerate(columns))
        if excludes_sql:
            bindings.update({
                f"{param_key}exclude{idx}": f"%{exc.replace(' ', '%').replace('%%', ' ')}%"
                for idx, exc in enumerate(exclude)
            })

        search_sql = []
        if includes_sql:
            search_sql.append(f"({includes_sql})")
        if excludes_sql:
            search_sql.append(excludes_sql)

        return search_sql, bindings

    def _fts_search_sql(self, table, fts_table, include, exclude=None, flexible=False):
        param_key = f"S_FTS_{os.urandom(4).hex()}"
        param_value = " OR ".join(f'"{term}"' for term in include) if flexible else " AND ".join(f'"{term}"' for term in include)
        if exclude:
            param_value += " NOT " + " AND NOT ".join(f'"{term}"' for term in exclude)
        return f"""
        WITH original AS (SELECT rowid, * FROM {table})
        SELECT original.*, {fts_table}.rank
        FROM original
        JOIN {fts_table} ON original.rowid = {fts_table}.rowid
        WHERE {fts_table} MATCH :{param_key}
        """, {param_key: param_value}

    def _construct_search_filter(self, conn, include=None, exclude=None, exact=False, flexible_search=False):
        m_columns = self._get_columns(conn, "media")
        is_fts = self._detect_fts(conn, "media_fts")
        if is_fts and include:
            table, search_bindings = self._fts_search_sql("media", is_fts, include, exclude, flexible_search)
            m_columns["rank"] = int
        else:
            columns = [f"m.{k}" for k in m_columns if k in ["title", "path", "time"]]
            table, search_bindings = "media", self._construct_search_bindings(include, exclude, columns, exact, flexible_search)

        return table, m_columns, filter_sql, search_bindings

    def _merge_captions(self, captions):
        def get_end(caption):
            return caption["time"] + (len(caption["text"]) / 4.2 / 220 * 60)

        merged_captions = []
        for path, group in itertools.groupby(sorted(captions, key=lambda x: x["path"]), key=lambda x: x["path"]):
            group = list(group)
            if not group:
                continue
            merged_group = {
                "path": path,
                "time": group[0]["time"],
                "end": get_end(group[0]),
                "text": group[0]["text"],
                "title": group[0]["title"],
            }
            for caption in group[1:]:
                end = get_end(caption)
                if abs(caption["time"] - merged_group["end"]) <= 0.5:
                    merged_group["end"] = end
                    if caption["text"] not in merged_group["text"]:
                        merged_group["text"] += ". " + caption["text"]
                else:
                    merged_captions.append(merged_group)
                    merged_group = {
                        "path": path,
                        "time": caption["time"],
                        "end": end,
                        "text": caption["text"],
                        "title": caption["title"],
                    }
            merged_captions.append(merged_group)
        return merged_captions

    def _construct_captions_search_query(self, conn, term, limit=None, sort="path, time"):
        table, m_columns, filter_sql, filter_bindings = self._construct_search_filter(
            conn, include=[term], exclude=[], exact=False, flexible_search=False
        )

        select_columns = ["path", "text", "time", "title"]
        select_sql = ", ".join(select_columns)
        limit_sql = f"LIMIT {limit}" if limit else ""

        query = f"""
        WITH c AS (
            SELECT * FROM captions
            WHERE {" AND ".join(filter_sql) if filter_sql else "1=1"}
        ),
        original AS (
            SELECT rowid, * FROM media
        )
        SELECT c.path, c.text, c.time, c.title
        FROM c
        JOIN original ON original.rowid = c.media_id
        JOIN media_fts ON original.rowid = media_fts.rowid
        WHERE media_fts MATCH :S_FTS_d66c8328
        ORDER BY {sort}
        {limit_sql}
        """

        return query, filter_bindings

    def get_search_terms(self, term):
        if not term:
            return []

        log.debug("Searching in DB: %s", self.db_file)
        try:
            with self._connect() as conn:
                query, bindings = self._construct_captions_search_query(conn, term)
                log.debug("Query: %s", query)
                log.debug("Bindings: %s", bindings)
                captions = conn.execute(query, bindings).fetchall()
                captions_dict = [dict(zip(["path", "text", "time", "title"], row)) for row in captions]
                merged_captions = self._merge_captions(captions_dict)
                self._print_caps(merged_captions)
                return [row["title"] for row in merged_captions]
        except sqlite3.Error as ex:
            log.error("Error querying the database: %s", ex)
            return []

    def _print_caps(self, captions):
        filtered_captions = [c for c in captions if any(v for v in c.values())]
        for caption in filtered_captions:
            print(f"{caption['path']} {caption['time']} {caption['text']}")
            log.debug(f"{caption['path']} {caption['time']} {caption['text']}")
        print()
