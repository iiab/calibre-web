from types import SimpleNamespace
from unittest.mock import Mock

from flask import Flask
from sqlalchemy.exc import OperationalError

from cps.db import CalibreDB


def test_get_cc_columns_returns_empty_list_when_custom_columns_table_is_missing():
    calibre_db = CalibreDB()
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.all.side_effect = OperationalError(
        "SELECT * FROM custom_columns",
        {},
        Exception("no such table: custom_columns"),
    )
    calibre_db.connect = Mock(return_value=mock_session)

    config = SimpleNamespace(config_columns_to_ignore=None, config_read_column=None)

    with Flask(__name__).app_context():
        assert calibre_db.get_cc_columns(config) == []
        assert calibre_db.get_browseable_cc_columns(config) == []
