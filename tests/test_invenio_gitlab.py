# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 HZDR
#
# This file is part of RODARE.
#
# invenio-gitlab is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# invenio-gitlab is distributed in the hope that
# it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Rodare. If not, see <http://www.gnu.org/licenses/>.

"""Module tests."""

from __future__ import absolute_import, print_function

import pytest
from flask import Flask
from invenio_db.utils import drop_alembic_version_table

from invenio_gitlab import InvenioGitLab


def test_version():
    """Test version import."""
    from invenio_gitlab import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    ext = InvenioGitLab(app)
    assert 'invenio-gitlab' in app.extensions

    app = Flask('testapp')
    ext = InvenioGitLab()
    assert 'invenio-gitlab' not in app.extensions
    ext.init_app(app)
    assert 'invenio-gitlab' in app.extensions


def test_alembic(app, db):
    """Test alembic recipes."""
    ext = app.extensions['invenio-db']

    if db.engine.name == 'sqlite':
        raise pytest.skip('Upgrades are not supported on SQLite.')

    assert not ext.alembic.compare_metadata()
    db.drop_all()
    drop_alembic_version_table()
    ext.alembic.upgrade()

    assert not ext.alembic.compare_metadata()
    ext.alembic.stamp()
    ext.alembic.downgrade(target='96e796392533')
    ext.alembic.upgrade()

    assert not ext.alembic.compare_metadata()
    drop_alembic_version_table()
