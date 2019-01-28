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

"""Test view of Gitlab integration for Invenio."""

import json

from flask import url_for
from helpers import GitlabMock, _get_state, login_user, mock, mock_response

from invenio_gitlab.api import GitLabAPI
from invenio_gitlab.models import Project


@mock.patch('gitlab.Gitlab')
def test_settings_index(mock_gl, app, client, db, user, example_gitlab):
    """Test settings index view."""
    example_email = 'test1@hzdr.de'
    mock_gl.return_value = GitlabMock(
        'https://gitlab.com',
        oauth_token='123456', email=example_email,
    )

    url = url_for('invenio_gitlab.index')
    resp = client.get(url)
    # expect redirect to login form
    assert resp.status_code == 302
    assert '/login' in resp.location

    login_user(client, user)
    resp = client.get(url)
    assert resp.status_code == 200
    assert 'Connect' in resp.get_data(as_text=True)

    # Connect user account with GitLab
    mock_response(app.extensions['oauthlib.client'], 'gitlab',
                  example_gitlab)
    resp = client.get(
        url_for('invenio_oauthclient.authorized',
                remote_app='gitlab', code='test', state=_get_state())
    )
    assert resp.status_code == 302
    assert resp.location == (
        'http://localhost.localdomain' +
        url_for('invenio_oauthclient_settings.index')
    )
    resp = client.get(url)
    assert resp.status_code == 200
    resp_text = resp.get_data(as_text=True)
    assert 'test/test' in resp_text
    assert 'https://gitlab.com/test/test' in resp_text
    gitlab = GitLabAPI(user_id=user.id)
    projects = gitlab.account.extra_data['projects']
    assert '1234' in projects

    # Test webhook creation
    headers = {'Content-Type': 'application/json'}
    url = url_for('invenio_gitlab.hook')
    # Project id not available.
    resp = client.post(url, data=json.dumps(dict(id='5587')), headers=headers)
    assert resp.status_code == 404

    # Enable the webhook.
    resp = client.post(url, data=json.dumps(dict(id='1234')), headers=headers)
    assert resp.status_code == 201
    project = Project.get(user_id=user.id, gitlab_id='1234', name='test/test')
    assert project.enabled
    assert project.hook == 123

    # Disable the webhook.
    resp = client.delete(url,
                         data=json.dumps(dict(id='1234')), headers=headers)
    assert resp.status_code == 204
    project = Project.get(user_id=user.id, gitlab_id='1234', name='test/test')
    assert not project.enabled
    assert not project.hook


def test_settings_project(app, client, db, user, project):
    """Test detail page of selected project."""
    url = url_for('invenio_gitlab.project', name='test/test')
    resp = client.get(url)
    # expect redirect to login form
    assert resp.status_code == 302
    assert '/login' in resp.location


def test_pattern_configuration(app, client, db, user, project):
    """Test changing of the release regular expression."""
    url = url_for('invenio_gitlab.pattern')
    resp = client.post(url)
    # expect redirect to login form
    assert resp.status_code == 302
    assert '/login' in resp.location

    headers = {'Content-Type': 'application/json'}
    login_user(client, user)
    # Test without given project ID.
    resp = client.post(url, data='{}', headers=headers)
    assert resp.status_code == 400

    # Test with unavailable project.
    data = {'id': 403}
    resp = client.post(url, data=json.dumps(data), headers=headers)
    assert resp.status_code == 403

    # Test with project ID, without pattern.
    data['id'] = 1234
    resp = client.post(url, data=json.dumps(data), headers=headers)
    assert resp.status_code == 400

    # Test with valid pattern
    data['pattern'] = 'v1*'
    resp = client.post(url, data=json.dumps(data), headers=headers)
    assert resp.status_code == 204
    project_instance = Project.get(user_id=user.id,
                                   gitlab_id=1234)
    assert project_instance.release_pattern == data['pattern']

    # Reset pattern to the default value
    data.pop('pattern')
    resp = client.delete(url, data=json.dumps(data), headers=headers)
    assert resp.status_code == 204
    project_instance = Project.get(user_id=user.id,
                                   gitlab_id=1234)
    assert project_instance.release_pattern == 'v*'
