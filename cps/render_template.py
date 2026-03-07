# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2020 OzzieIsaacs
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

from flask import render_template, g, abort, request
from flask_babel import gettext as _
from werkzeug.local import LocalProxy
from .cw_login import current_user
from sqlalchemy.sql.expression import or_

from . import config, constants, logger, ub, calibre_db, db
from .ub import User
from .media_context import detect_library_media_context


log = logger.create()

def get_sidebar_config(kwargs=None):
    kwargs = kwargs or []
    simple = bool([e for e in ['kindle', 'tolino', "kobo", "bookeen"]
                   if (e in request.headers.get('User-Agent', "").lower())])
    media_context = kwargs.get("media_context") if isinstance(kwargs, dict) else None
    if not media_context:
        media_context = detect_library_media_context(calibre_db, db)
    label_sets = {
        "book": {"root": _('Books'), "hot": _('Hot Books'), "people": _('Authors'),
                 "downloaded": _('Downloaded Books'), "top_rated": _('Top Rated Books'),
                 "read": _('Read Books'), "unread": _('Unread Books'),
                 "archived": _('Archived Books'), "list": _('Books List')},
        "video": {"root": _('Videos'), "hot": _('Popular Videos'), "people": _('Creators'),
                  "downloaded": _('Downloaded Videos'), "top_rated": _('Top Rated Videos'),
                  "read": _('Viewed Videos'), "unread": _('Unviewed Videos'),
                  "archived": _('Archived Videos'), "list": _('Video List')},
        "audio": {"root": _('Audio'), "hot": _('Popular Audio'), "people": _('Creators'),
                  "downloaded": _('Downloaded Audio'), "top_rated": _('Top Rated Audio'),
                  "read": _('Listened Audio'), "unread": _('Unlistened Audio'),
                  "archived": _('Archived Audio'), "list": _('Audio List')},
        "image": {"root": _('Images'), "hot": _('Popular Images'), "people": _('Creators'),
                  "downloaded": _('Downloaded Images'), "top_rated": _('Top Rated Images'),
                  "read": _('Viewed Images'), "unread": _('Unviewed Images'),
                  "archived": _('Archived Images'), "list": _('Image List')},
    }
    labels = label_sets.get(media_context, label_sets["book"])
    if 'content' in kwargs:
        content = kwargs['content']
        content = isinstance(content, (User, LocalProxy)) and not content.role_anonymous()
    else:
        content = 'conf' in kwargs
    sidebar = list()
    sidebar.append({"glyph": "glyphicon-book", "text": labels["root"], "link": 'web.index', "id": "new",
                    "visibility": constants.SIDEBAR_RECENT, 'public': True, "page": "root",
                    "show_text": _('Show recent books'), "config_show":False})
    sidebar.append({"glyph": "glyphicon-fire", "text": labels["hot"], "link": 'web.books_list', "id": "hot",
                    "visibility": constants.SIDEBAR_HOT, 'public': True, "page": "hot",
                    "show_text": _('Show Hot Books'), "config_show": True})
    if current_user.role_admin():
        sidebar.append({"glyph": "glyphicon-download", "text": labels["downloaded"], "link": 'web.download_list',
                        "id": "download", "visibility": constants.SIDEBAR_DOWNLOAD, 'public': (not current_user.is_anonymous),
                        "page": "download", "show_text": _('Show Downloaded Books'), "no_param":True,
                        "config_show": content})
    else:
        sidebar.append({"glyph": "glyphicon-download", "text": labels["downloaded"], "link": 'web.books_list',
                        "id": "download", "visibility": constants.SIDEBAR_DOWNLOAD, 'public': (not current_user.is_anonymous),
                        "page": "download", "show_text": _('Show Downloaded Books'),
                        "config_show": content})
    sidebar.append(
        {"glyph": "glyphicon-star", "text": labels["top_rated"], "link": 'web.books_list', "id": "rated",
         "visibility": constants.SIDEBAR_BEST_RATED, 'public': True, "page": "rated",
         "show_text": _('Show Top Rated Books'), "config_show": True})
    sidebar.append({"glyph": "glyphicon-eye-open", "text": labels["read"], "link": 'web.books_list', "id": "read",
                    "visibility": constants.SIDEBAR_READ_AND_UNREAD, 'public': (not current_user.is_anonymous),
                    "page": "read", "show_text": _('Show Read and Unread'), "config_show": content})
    sidebar.append(
        {"glyph": "glyphicon-eye-close", "text": labels["unread"], "link": 'web.books_list', "id": "unread",
         "visibility": constants.SIDEBAR_READ_AND_UNREAD, 'public': (not current_user.is_anonymous), "page": "unread",
         "show_text": _('Show unread'), "config_show": False})
    sidebar.append({"glyph": "glyphicon-random", "text": _('Discover'), "link": 'web.books_list', "id": "rand",
                    "visibility": constants.SIDEBAR_RANDOM, 'public': True, "page": "discover",
                    "show_text": _('Show Random Books'), "config_show": True})
    sidebar.append({"glyph": "glyphicon-inbox", "text": _('Categories'), "link": 'web.category_list', "id": "cat",
                    "visibility": constants.SIDEBAR_CATEGORY, 'public': True, "page": "category", "no_param":True,
                    "show_text": _('Show Category Section'), "config_show": True})
    sidebar.append({"glyph": "glyphicon-bookmark", "text": _('Series'), "link": 'web.series_list', "id": "serie",
                    "visibility": constants.SIDEBAR_SERIES, 'public': True, "page": "series", "no_param":True,
                    "show_text": _('Show Series Section'), "config_show": True})
    sidebar.append({"glyph": "glyphicon-user", "text": labels["people"], "link": 'web.author_list', "id": "author",
                    "visibility": constants.SIDEBAR_AUTHOR, 'public': True, "page": "author", "no_param":True,
                    "show_text": _('Show Author Section'), "config_show": True})
    sidebar.append({"glyph": "glyphicon-film", "text": _('Videos'), "link": 'web.books_list', "id": "videos",
                    "visibility": constants.SIDEBAR_RECENT, 'public': True, "page": "videos",
                    "show_text": _('Show Videos'), "config_show": True})
    sidebar.append({"glyph": "glyphicon-music", "text": _('Audio'), "link": 'web.books_list', "id": "audios",
                    "visibility": constants.SIDEBAR_RECENT, 'public': True, "page": "audios",
                    "show_text": _('Show Audio'), "config_show": True})
    sidebar.append({"glyph": "glyphicon-picture", "text": _('Images'), "link": 'web.books_list', "id": "images",
                    "visibility": constants.SIDEBAR_RECENT, 'public': True, "page": "images",
                    "show_text": _('Show Images'), "config_show": True})
    sidebar.append({"glyph": "glyphicon-book", "text": _('Books'), "link": 'web.books_list', "id": "books",
                    "visibility": constants.SIDEBAR_RECENT, 'public': True, "page": "books",
                    "show_text": _('Show Books'), "config_show": True})
    sidebar.append(
        {"glyph": "glyphicon-text-size", "text": _('Publishers'), "link": 'web.publisher_list', "id": "publisher",
         "visibility": constants.SIDEBAR_PUBLISHER, 'public': True, "page": "publisher", "no_param":True,
         "show_text": _('Show Publisher Section'), "config_show":True})
    sidebar.append({"glyph": "glyphicon-flag", "text": _('Languages'), "link": 'web.language_overview', "id": "lang",
                    "visibility": constants.SIDEBAR_LANGUAGE, 'public': (current_user.filter_language() == 'all'),
                    "page": "language", "no_param":True,
                    "show_text": _('Show Language Section'), "config_show": True})
    sidebar.append({"glyph": "glyphicon-star-empty", "text": _('Ratings'), "link": 'web.ratings_list', "id": "rate",
                    "visibility": constants.SIDEBAR_RATING, 'public': True, "no_param":True,
                    "page": "rating", "show_text": _('Show Ratings Section'), "config_show": True})
    sidebar.append({"glyph": "glyphicon-file", "text": _('File formats'), "link": 'web.formats_list', "id": "format",
                    "visibility": constants.SIDEBAR_FORMAT, 'public': True, "no_param":True,
                    "page": "format", "show_text": _('Show File Formats Section'), "config_show": True})
    sidebar.append(
        {"glyph": "glyphicon-folder-open", "text": labels["archived"], "link": 'web.books_list', "id": "archived",
         "visibility": constants.SIDEBAR_ARCHIVED, 'public': (not current_user.is_anonymous), "page": "archived",
         "show_text": _('Show Archived Books'), "config_show": content})
    if not simple:
        sidebar.append(
            {"glyph": "glyphicon-th-list", "text": labels["list"], "link": 'web.books_table', "id": "list",
             "visibility": constants.SIDEBAR_LIST, 'public': (not current_user.is_anonymous),
             "show_text": _('Show Books List'), "config_show": content, "no_param":True})
    g.shelves_access = ub.session.query(ub.Shelf).filter(
        or_(ub.Shelf.is_public == 1, ub.Shelf.user_id == current_user.id)).order_by(ub.Shelf.name).all()

    return sidebar, simple


# Returns the template for rendering and includes the instance name
def render_title_template(*args, **kwargs):
    sidebar, simple = get_sidebar_config(kwargs)
    try:
        return render_template(instance=config.config_calibre_web_title, sidebar=sidebar, simple=simple,
                               accept=config.config_upload_formats.split(','),
                               *args, **kwargs)
    except PermissionError:
        log.error("No permission to access {} file.".format(args[0]))
        abort(403)
