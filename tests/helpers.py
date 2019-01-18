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

"""Helper functions for tests."""

from invenio_oauthclient._compat import _create_identifier
from invenio_oauthclient.views.client import serializer

try:
    from unittest import mock
except ImportError:
    import mock


def login_user(client, user):
    """Log in a specified user."""
    with client.session_transaction() as sess:
        sess['user_id'] = user.id if user else None
        sess['_fresh'] = True


def mock_response(oauth, remote_app='gitlab', data=None):
    """Mock the oauth response to use the remote."""
    oauth.remote_apps[remote_app].handle_oauth2_response = mock.MagicMock(
        return_value=data
    )


def _get_state():
    return serializer.dumps({'app': 'gitlab', 'sid': _create_identifier(),
                             'next': None, })


class GLUser(object):
    """User class for mocking GitLab API."""

    def __init__(self, email):
        """Init user."""
        self.email = email

    @property
    def attributes(self):
        """Return user attributes."""
        return {
            'id': 1234,
            'name': 'Test Test',
            'username': 'test',
            'state': 'active',
            'email': self.email,
        }


class Hook(object):
    """Hook object for mocking GitLab API."""

    def __init__(self, id=123):
        """Init."""
        self.id = id


class Hooks(object):
    """Hooks class for mocking GitLab API."""

    def list(self):
        """Return list of installed hooks."""
        return []

    def create(self, attributes):
        """Create GitLab webhook."""
        return Hook()


class GLProjects(object):
    """Class for mocking a GitLab project."""

    def __init__(self, id=1234, name='test', path_with_namespace='test/test'):
        """Init project."""
        self.id = id
        self.name = name
        self.path_with_namespace = path_with_namespace
        self.hooks = Hooks()

    @property
    def attributes(self):
        """Project attributes."""
        return dict(
            id=self.id,
            description='Test project description.',
            name=self.name,
            path_with_namespace=self.path_with_namespace,
            created_at='2018-08-07T18:31:43.564Z',
        )


class ProjectList(object):
    """GitLab project lists mock."""

    def list(self, owned=False, simple=False):
        """List GitLab projects."""
        return [GLProjects()]

    def get(self, project_id):
        """Return project."""
        return self.list()[0]


class GitlabMock(object):
    """Mock GitLab API."""

    def __init__(self, server, oauth_token, email='info@hzdr.de'):
        """Init mock."""
        self.user = GLUser(email)

    def auth(self):
        """Mock auth."""
        return True

    @property
    def projects(self):
        """Gitlab projects API."""
        return ProjectList()
