import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from flask import Flask
from sqlalchemy.exc import OperationalError

from cps import db as cps_db
from cps.db import CalibreDB


def _column(column_id, datatype, normalized=True):
    return SimpleNamespace(id=column_id, datatype=datatype, normalized=normalized,
                           name='column %s' % column_id, label='column_%s' % column_id)


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


def test_get_browseable_cc_columns_skips_datatypes_without_url_safe_values(monkeypatch):
    monkeypatch.setattr(cps_db, 'cc_classes', {1: object(), 2: object(), 3: object()})
    calibre_db = CalibreDB()
    calibre_db.get_cc_columns = Mock(return_value=[_column(1, 'text'),
                                                   _column(2, 'comments'),
                                                   _column(3, 'int')])
    config = SimpleNamespace(config_custom_sidebar_columns={})

    with Flask(__name__).app_context():
        assert [c.id for c in calibre_db.get_browseable_cc_columns(config)] == [1]


def test_get_browseable_cc_columns_uses_sidebar_settings(monkeypatch):
    monkeypatch.setattr(cps_db, 'cc_classes', {1: object(), 2: object(), 3: object()})
    calibre_db = CalibreDB()
    calibre_db.get_cc_columns = Mock(return_value=[_column(1, 'text'),
                                                   _column(2, 'int'),
                                                   _column(3, 'rating')])
    config = SimpleNamespace(config_custom_sidebar_columns={'1': False, '2': True, '3': False})

    with Flask(__name__).app_context():
        assert [c.id for c in calibre_db.get_browseable_cc_columns(config)] == [2]


def test_remove_db_cc_class(monkeypatch):
    monkeypatch.setattr(cps_db, 'cc_classes', {7: object()})
    CalibreDB.remove_db_cc_class(7)
    assert 7 not in cps_db.cc_classes


def test_parse_custom_column_value():
    from cps import cli_param
    cli_param.gd_path = ':memory:'
    from cps.helper import parse_custom_column_value

    assert parse_custom_column_value(SimpleNamespace(datatype='bool'), 'True') is True
    assert parse_custom_column_value(SimpleNamespace(datatype='bool'), '1') is True
    assert parse_custom_column_value(SimpleNamespace(datatype='bool'), 'false') is False
    assert parse_custom_column_value(SimpleNamespace(datatype='int'), '42') == 42
    assert parse_custom_column_value(SimpleNamespace(datatype='float'), '2.5') == 2.5
    assert parse_custom_column_value(SimpleNamespace(datatype='datetime'),
                                     '2021-01-02 03:04:05') == datetime.datetime(2021, 1, 2, 3, 4, 5)
    assert parse_custom_column_value(SimpleNamespace(datatype='text'), 'abc') == 'abc'
    with pytest.raises(ValueError):
        parse_custom_column_value(SimpleNamespace(datatype='int'), 'abc')
