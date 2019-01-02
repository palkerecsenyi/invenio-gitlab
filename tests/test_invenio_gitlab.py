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

from flask import Flask

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


def test_view(app):
    """Test view."""
    InvenioGitLab(app)
    with app.test_client() as client:
        res = client.get("/")
        assert res.status_code == 200
        assert 'Welcome to Invenio-GitLab' in str(res.data)
