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

"""Minimal Flask application example.

SPHINX-START

First install Invenio-GitLab, setup the application and load
fixture data by running:

.. code-block:: console

   $ pip install -e .[all]
   $ cd examples
   $ ./app-setup.sh
   $ ./app-fixtures.sh

Next, start the development server:

.. code-block:: console

   $ export FLASK_APP=app.py FLASK_DEBUG=1
   $ flask run

and open the example application in your browser:

.. code-block:: console

    $ open http://127.0.0.1:5000/

To reset the example application run:

.. code-block:: console

    $ ./app-teardown.sh

SPHINX-END
"""

from __future__ import absolute_import, print_function

import os

from flask import Flask, redirect, render_template, url_for
from flask_babelex import Babel
from flask_celeryext import FlaskCeleryExt
from flask_login import current_user
from flask_menu import Menu as FlaskMenu
from invenio_accounts import InvenioAccounts
from invenio_accounts.views.settings import blueprint as accounts_blueprint
from invenio_assets import InvenioAssets
from invenio_db import InvenioDB
from invenio_deposit import InvenioDeposit, InvenioDepositREST
from invenio_files_rest import InvenioFilesREST
from invenio_i18n import InvenioI18N
from invenio_indexer import InvenioIndexer
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_oauth2server import InvenioOAuth2Server
from invenio_oauth2server.views import server_blueprint, settings_blueprint
from invenio_oauthclient import InvenioOAuthClient
from invenio_oauthclient.views.client import blueprint as oauthclient_blueprint
from invenio_oauthclient.views.settings import \
    blueprint as oauthclient_settings_blueprint
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from invenio_records_rest import InvenioRecordsREST
from invenio_records_rest.utils import PIDConverter
from invenio_search import InvenioSearch
from invenio_search_ui import InvenioSearchUI
from invenio_theme import InvenioTheme
from invenio_webhooks import InvenioWebhooks
from invenio_webhooks.views import blueprint as webhooks_blueprint

from invenio_gitlab import InvenioGitLab
from invenio_gitlab.config import REMOTE_APP
from invenio_gitlab.views.gitlab import blueprint as gl_settings_blueprint

# Create Flask application
app = Flask(__name__)

app.config.update(
    ACCOUNTS_SESSION_REDIS_URL=os.getenv('ACCOUNTS_SESSION_REDIS_URL',
                                         'redis://localhost:6379/0'),
    CACHE_TYPE='simple',
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_CACHE_BACKEND='memory',
    CELERY_TASK_EAGER_PROPAGATES=True,
    CELERY_RESULT_BACKEND='cache',
    GITLAB_APP_CREDENTIALS=dict(
        consumer_key='gitlab_key_changeme',
        consumer_secret='gitlab_secret_changeme',
    ),
    GITLAB_INSECURE_SSL=True,
    GITLAB_WEBHOOK_RECEIVER_URL='http://localhost:5000'
                                '/hooks/receivers/gitlab/events/'
                                '?access_token={token}',
    OAUTHLIB_INSECURE_TRANSPORT=True,
    OAUTH2_CACHE_TYPE='simple',
    OAUTHCLIENT_REMOTE_APPS=dict(
        gitlab=REMOTE_APP,
    ),
    SECRET_KEY='SECRET_KEY',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI',
                                      'sqlite:///test.db'),
    SECURITY_PASSWORD_HASH='plaintext',
    SECURITY_PASSWORD_SCHEMES=['plaintext'],
    SECURITY_DEPRECATED_PASSWORD_SCHEMES=[],
    SERVER_NAME='localhost:5000',
    TESTING=True,
    WTF_CSRF_ENABLED=False,
)

app.url_map.converters['pid'] = PIDConverter

celeryext = FlaskCeleryExt(app)
Babel(app)
InvenioDB(app)
InvenioAssets(app)
InvenioTheme(app)
InvenioI18N(app)
InvenioAccounts(app)
app.register_blueprint(accounts_blueprint)
InvenioOAuthClient(app)
app.register_blueprint(oauthclient_blueprint)
app.register_blueprint(oauthclient_settings_blueprint)
InvenioOAuth2Server(app)
app.register_blueprint(server_blueprint)
app.register_blueprint(settings_blueprint)
InvenioPIDStore(app)
InvenioRecords(app)
InvenioSearch(app)
InvenioSearchUI(app)
InvenioIndexer(app)
InvenioFilesREST(app)
InvenioRecordsREST(app)
InvenioDepositREST(app)
InvenioDeposit(app)
InvenioWebhooks(app)
celeryext.celery.flask_app = app  # Make sure both apps are the same!
app.register_blueprint(webhooks_blueprint)

InvenioGitLab(app)
app.register_blueprint(gl_settings_blueprint)


@app.route('/')
def index():
    """Index."""
    return render_template('invenio_theme/frontpage.html')


@app.route('/gitlab')
def gitlab():
    """Print user email or redirect to login with GitLab."""
    if not current_user.is_authenticated:
        return redirect(url_for('invenio_oauthclient.login',
                                remote_app='gitlab'))
    return 'Hello {}'.format(current_user.email)
