import datetime
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from flask import Flask
from sqlalchemy import Column, Integer
from sqlalchemy.exc import OperationalError

from cps import db as cps_db
from cps.db import AlchemyEncoder, Base, CalibreDB


class BookWithDeletedCustomColumn(Base):
    __tablename__ = 'book_with_deleted_custom_column'
    id = Column(Integer, primary_key=True)

    @property
    def custom_column_99(self):
        raise AssertionError("relationship of a deleted custom column was read")


class BookWithRegisteredCustomColumn(Base):
    __tablename__ = 'book_with_registered_custom_column'
    id = Column(Integer, primary_key=True)

    @property
    def custom_column_1(self):
        return 'value'


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


def test_alchemy_encoder_skips_deleted_custom_columns(monkeypatch):
    monkeypatch.setattr(cps_db, 'cc_classes', {})
    encoded = json.loads(json.dumps(BookWithDeletedCustomColumn(id=1), cls=AlchemyEncoder))
    assert encoded['id'] == 1
    assert 'custom_column_99' not in encoded


def test_alchemy_encoder_keeps_registered_custom_columns(monkeypatch):
    monkeypatch.setattr(cps_db, 'cc_classes', {1: object()})
    encoded = json.loads(json.dumps(BookWithRegisteredCustomColumn(id=2), cls=AlchemyEncoder))
    assert encoded['custom_column_1'] == 'value'


def test_parse_custom_column_value():
    from cps import cli_param
    cli_param.gd_path = ':memory:'
    from cps.helper import parse_custom_column_value

    assert parse_custom_column_value(SimpleNamespace(datatype='bool'), 'True') is True
    assert parse_custom_column_value(SimpleNamespace(datatype='bool'), '1') is True
    assert parse_custom_column_value(SimpleNamespace(datatype='bool'), 'yes') is True
    assert parse_custom_column_value(SimpleNamespace(datatype='bool'), 'false') is False
    assert parse_custom_column_value(SimpleNamespace(datatype='bool'), '0') is False
    assert parse_custom_column_value(SimpleNamespace(datatype='bool'), 'no') is False
    with pytest.raises(ValueError):
        parse_custom_column_value(SimpleNamespace(datatype='bool'), 'garbage')
    assert parse_custom_column_value(SimpleNamespace(datatype='int'), '42') == 42
    assert parse_custom_column_value(SimpleNamespace(datatype='float'), '2.5') == 2.5
    assert parse_custom_column_value(SimpleNamespace(datatype='datetime'),
                                     '2021-01-02 03:04:05') == datetime.datetime(2021, 1, 2, 3, 4, 5)
    assert parse_custom_column_value(SimpleNamespace(datatype='text'), 'abc') == 'abc'
    with pytest.raises(ValueError):
        parse_custom_column_value(SimpleNamespace(datatype='int'), 'abc')


def test_add_restriction_keeps_custom_column_allow_and_deny_lists_separate(monkeypatch):
    from cps import admin

    config = SimpleNamespace(
        config_allowed_column_value='existing_allowed',
        config_denied_column_value='existing_denied',
        save=Mock(),
    )
    config.list_allowed_column_values = lambda: config.config_allowed_column_value.split(',')
    config.list_denied_column_values = lambda: config.config_denied_column_value.split(',')
    monkeypatch.setattr(admin, 'config', config)

    add_restriction = admin.add_restriction.__wrapped__.__wrapped__
    with Flask(__name__).test_request_context(
            '/ajax/addrestriction/1', method='POST',
            data={'submit_allow': '', 'add_element': 'new_allowed'}):
        add_restriction(1, 0)
    assert config.config_allowed_column_value == 'existing_allowed,new_allowed'
    assert config.config_denied_column_value == 'existing_denied'

    with Flask(__name__).test_request_context(
            '/ajax/addrestriction/1', method='POST',
            data={'submit_deny': '', 'add_element': 'new_denied'}):
        add_restriction(1, 0)
    assert config.config_allowed_column_value == 'existing_allowed,new_allowed'
    assert config.config_denied_column_value == 'existing_denied,new_denied'
