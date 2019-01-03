# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 HZDR
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

"""Pytest configuration."""

from __future__ import absolute_import, print_function

import json
import os
import shutil
import tempfile

import pytest
from flask import Flask
from flask_babelex import Babel
from flask_celeryext import FlaskCeleryExt
from invenio_accounts import InvenioAccounts
from invenio_db import InvenioDB
from invenio_db import db as db_
from invenio_webhooks import InvenioWebhooks
from invenio_webhooks.views import blueprint as webhooks_blueprint
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_gitlab import InvenioGitLab


@pytest.fixture()
def instance_path():
    """Temporary instance path."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture()
def base_app(instance_path):
    """Flask application fixture."""
    app_ = Flask('testapp', instance_path=instance_path)
    app_.config.update(
        CACHE_TYPE='simple',
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_CACHE_BACKEND='memory',
        CELERY_TASK_EAGER_PROPAGATES=True,
        CELERY_RESULT_BACKEND='cache',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI',
                                          'sqlite://'),
        SECRET_KEY='SECRET_KEY',
        TESTING=True,
    )
    celeryext = FlaskCeleryExt(app_)
    InvenioDB(app_)
    InvenioAccounts(app_)
    InvenioWebhooks(app_)
    celeryext.celery.flask_app = app_  # Make sure both apps are the same!
    app_.register_blueprint(webhooks_blueprint)

    return app_


@pytest.fixture()
def app(base_app):
    """Flask application fixture."""
    InvenioGitLab(base_app)
    with base_app.app_context():
        yield base_app


@pytest.fixture()
def db(app):
    """Get setup database."""
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))
    db_.create_all()
    yield db_
    db_.session.remove()
    db_.drop_all()


@pytest.fixture()
def tester_id(app, db):
    """Fixture that contains the test data for models tests."""
    datastore = app.extensions['security'].datastore
    tester = datastore.create_user(
        email='tester@hzdr.de', password='tester',
    )
    db.session.commit()
    return tester.id


@pytest.fixture()
def hook_response():
    """Fixture that returns a sample dictionary the same as the GitLab API."""
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data',
        'gitlab_tag_hook.json'
    )
    with open(path) as f:
        data = json.load(f)
    return data
