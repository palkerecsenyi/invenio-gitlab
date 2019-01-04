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
from flask_mail import Mail
from flask_menu import Menu as FlaskMenu
from flask_oauthlib.client import OAuth as FlaskOAuth
from invenio_accounts import InvenioAccounts
from invenio_db import InvenioDB
from invenio_db import db as db_
from invenio_oauth2server import InvenioOAuth2Server
from invenio_oauthclient import InvenioOAuthClient
from invenio_oauthclient.views.client import blueprint as blueprint_client
from invenio_oauthclient.views.settings import blueprint as settings_blueprint
from invenio_userprofiles import InvenioUserProfiles
from invenio_userprofiles.models import UserProfile
from invenio_webhooks import InvenioWebhooks
from invenio_webhooks.views import blueprint as webhooks_blueprint
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_gitlab import InvenioGitLab
from invenio_gitlab.handlers import REMOTE_APP as GITLAB_REMOTE_APP


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
        ACCOUNTS_SESSION_REDIS_URL=os.getenv('ACCOUNTS_SESSION_REDIS_URL',
                                             'redis://localhost:6379/0'),
        CACHE_TYPE='simple',
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_CACHE_BACKEND='memory',
        CELERY_TASK_EAGER_PROPAGATES=True,
        CELERY_RESULT_BACKEND='cache',
        # use local memory mailbox
        EMAIL_BACKEND='flask_email.backends.locmem.Mail',
        LOGIN_DISABLED=False,
        OAUTHCLIENT_REMOTE_APPS=dict(
            gitlab=GITLAB_REMOTE_APP,
        ),
        GITLAB_APP_CREDENTIALS=dict(
            consumer_key='gitlab_key_changeme',
            consumer_secret='gitlab_secret_changeme',
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI',
                                          'sqlite://'),
        SECRET_KEY='SECRET_KEY',
        SECURITY_DEPRECATED_PASSWORD_SCHEMES=[],
        SECURITY_PASSWORD_HASH='plaintext',
        SECURITY_PASSWORD_SCHEMES=['plaintext'],
        SERVER_NAME='localhost.localdomain',
        TESTING=True,
        USERPROFILES_EXTEND_SECURITY_FORMS=True,
        WTF_CSRF_ENABLED=True,
    )
    celeryext = FlaskCeleryExt(app_)
    InvenioDB(app_)
    InvenioAccounts(app_)
    Mail(app_)
    FlaskMenu(app_)
    InvenioWebhooks(app_)
    celeryext.celery.flask_app = app_  # Make sure both apps are the same!
    app_.register_blueprint(webhooks_blueprint)
    FlaskOAuth(app_)
    InvenioOAuthClient(app_)
    app_.register_blueprint(blueprint_client)
    app_.register_blueprint(settings_blueprint)
    InvenioOAuth2Server(app_)
    InvenioUserProfiles(app_)

    return app_


@pytest.fixture()
def app(base_app):
    """Flask application fixture."""
    InvenioGitLab(base_app)
    with base_app.app_context():
        yield base_app


@pytest.fixture()
def client(app):
    """Yield test client."""
    with app.test_client() as test_client:
        yield test_client


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


@pytest.fixture
def example_gitlab(request):
    """Gitlab example data."""
    return {
        "access_token": "test_access_token",
        "token_type": "bearer",
        "expires_in": 7200,
        "refresh_token": "test_refresh_token"
    }


@pytest.fixture()
def user(app, db):
    """Create users."""
    with db.session.begin_nested():
        datastore = app.extensions['security'].datastore
        user1 = datastore.create_user(email='info@hzdr.de',
                                      password='tester', active=True)
        profile = UserProfile(username='test', user=user1)
        db.session.add(profile)
    db.session.commit()
    return user1
