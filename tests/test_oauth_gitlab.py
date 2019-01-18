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

"""Test for GitLab oauth remote app."""

import pytest
from flask import session, url_for
from flask_login import current_user
from helpers import GitlabMock, _get_state, mock, mock_response
from invenio_accounts.models import User
from invenio_oauthclient.models import RemoteAccount, RemoteToken, UserIdentity
from six.moves.urllib_parse import parse_qs, urlparse


def test_login(client):
    """Test login via GitLab."""
    resp = client.get(
        url_for('invenio_oauthclient.login', remote_app='gitlab',
                next='/redirect/url/')
    )
    assert resp.status_code == 302

    params = parse_qs(urlparse(resp.location).query)
    assert params['response_type'], ['code']
    assert params['redirect_uri']
    assert params['client_id']
    assert params['state']


@mock.patch('gitlab.Gitlab')
def test_authorized_signup_valid_user(mock_gl, app,
                                      client, db, example_gitlab):
    """Test authorized handler with sign-up."""
    example_email = 'info@hzdr.de'
    mock_gl.return_value = GitlabMock(
        'https://gitlab.com',
        oauth_token='test',
        email=example_email,
    )

    resp = client.get(
        url_for('invenio_oauthclient.login', remote_app='gitlab')
    )

    assert resp.status_code == 302

    mock_response(app.extensions['oauthlib.client'], 'gitlab',
                  example_gitlab)
    # User authorized the request and is redirected back
    resp = client.get(
        url_for('invenio_oauthclient.authorized',
                remote_app='gitlab', code='test',
                state=_get_state()))
    assert resp.status_code == 302
    assert resp.location == ('http://localhost.localdomain' +
                             '/account/settings/linkedaccounts/')
    # Assert database state (Sign-up complete)
    user = User.query.filter_by(email=example_email).one()
    remote = RemoteAccount.query.filter_by(user_id=user.id).one()
    RemoteToken.query.filter_by(id_remote_account=remote.id).one()
    assert user.active

    # Disconnect users
    resp = client.get(
        url_for('invenio_oauthclient.disconnect', remote_app='gitlab'))
    assert resp.status_code == 302

    user = User.query.filter_by(email=example_email).one()
    assert 0 == UserIdentity.query.filter_by(
        method='gitlab', id_user=user.id,
        id='test'
    ).count()
    assert RemoteAccount.query.filter_by(user_id=user.id).count() == 0
    assert RemoteToken.query.count() == 0

    mock_gl.return_value = GitlabMock(
        'https://gitlab.com',
        oauth_token='test',
        email='info2@hzdr.de',
    )
    resp = client.get(
        url_for('invenio_oauthclient.authorized',
                remote_app='gitlab', code='test',
                state=_get_state()))
    assert resp.status_code == 302
    assert resp.location == (
        'http://localhost.localdomain/' +
        'account/settings/linkedaccounts/'
    )
    # check that exist only one account
    user = User.query.filter_by(email=example_email).one()
    assert User.query.count() == 1


@mock.patch('gitlab.Gitlab')
def test_authorized_signup_username_exists(mock_gl, app,
                                           client, db, example_gitlab):
    """Test authorized callback with no sign-up."""
    example_email = 'test1@hzdr.de'
    mock_gl.return_value = GitlabMock(
        'https://gitlab.com',
        oauth_token='123456', email=example_email,
    )
    # Ensure remote apps have been loaded (due to before first
    # request)
    resp = client.get(url_for('invenio_oauthclient.login',
                              remote_app='gitlab'))
    assert resp.status_code == 302

    mock_response(app.extensions['oauthlib.client'], 'gitlab',
                  example_gitlab)

    # User authorized the requests and is redirected back
    resp = client.get(
        url_for('invenio_oauthclient.authorized',
                remote_app='gitlab', code='test', state=_get_state())
    )
    assert resp.status_code == 302
    assert resp.location == (
        'http://localhost.localdomain' +
        url_for('invenio_oauthclient_settings.index')
    )

    # Assert database state (Sign-up complete)
    my_user = User.query.filter_by(email=example_email).one()
    remote = RemoteAccount.query.filter_by(user_id=my_user.id).one()
    RemoteToken.query.filter_by(id_remote_account=remote.id).one()
    assert my_user.active

    # Disconnect link
    resp = client.get(
        url_for('invenio_oauthclient.disconnect', remote_app='gitlab'))
    assert resp.status_code == 302

    # User exists
    my_user = User.query.filter_by(email=example_email).one()
    assert 0 == UserIdentity.query.filter_by(
        method='gitlab', id_user=my_user.id,
        id='test'
    ).count()
    assert RemoteAccount.query.filter_by(
        user_id=my_user.id).count() == 0
    assert RemoteToken.query.count() == 0
    assert User.query.count() == 1


def test_authorized_reject(app, client, db):
    """Test a rejected request."""
    resp = client.get(
        url_for('invenio_oauthclient.login', remote_app='gitlab'))
    assert resp.status_code == 302
    resp = client.get(
        url_for('invenio_oauthclient.authorized', remote_app='gitlab',
                error='acces_denied', error_description='User denied access',
                state=_get_state())
    )
    assert resp.status_code in (301, 302)
    assert resp.location == (
        'http://localhost.localdomain/'
    )
    # Check message flash
    assert session['_flashes'][0][0] == 'info'


def test_not_authenticated(app, client, db):
    """Test disconnect when user is not authenticated."""
    resp = client.get(
        url_for('invenio_oauthclient.disconnect', remote_app='gitlab')
    )
    assert resp.status_code == 302
