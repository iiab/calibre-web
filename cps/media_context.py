# -*- coding: utf-8 -*-

from . import constants


def get_media_extensions(media_type):
    media_type = (media_type or "all").lower()
    if media_type == "video":
        return constants.EXTENSIONS_VIDEO
    if media_type == "audio":
        return constants.EXTENSIONS_AUDIO
    if media_type == "image":
        return constants.EXTENSIONS_IMAGE
    if media_type == "book":
        return constants.EXTENSIONS_BOOK
    return set()


def get_media_db_filter(db, media_type):
    media_type = (media_type or "all").lower()
    if media_type == "all":
        return True
    exts = {ext.upper() for ext in get_media_extensions(media_type)}
    return db.Books.data.any(db.Data.format.in_(exts))


def detect_book_media_types(book):
    media_types = set()
    for fmt in book.data:
        lf = fmt.format.lower()
        if lf in constants.EXTENSIONS_VIDEO:
            media_types.add("video")
        if lf in constants.EXTENSIONS_AUDIO:
            media_types.add("audio")
        if lf in constants.EXTENSIONS_IMAGE:
            media_types.add("image")
        if lf in constants.EXTENSIONS_BOOK:
            media_types.add("book")
    if not media_types:
        media_types.add("book")
    return media_types


def detect_library_media_context(calibre_db, db):
    def count_for(exts):
        exts_upper = {e.upper() for e in exts}
        return (calibre_db.session.query(db.Books.id)
                .join(db.Data)
                .filter(calibre_db.common_filters())
                .filter(db.Data.format.in_(exts_upper))
                .distinct()
                .count())

    counts = {
        "video": count_for(constants.EXTENSIONS_VIDEO),
        "audio": count_for(constants.EXTENSIONS_AUDIO),
        "image": count_for(constants.EXTENSIONS_IMAGE),
        "book": count_for(constants.EXTENSIONS_BOOK),
    }

    dominant = max(counts, key=counts.get) if counts else "book"
    if counts.get(dominant, 0) == 0:
        return "book"
    return dominant
