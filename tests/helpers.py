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

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


def mock_response(oauth, remote_app='gitlab', data=None):
    """Mock the oauth response to use the remote."""
    oauth.remote_apps[remote_app].handle_oauth2_response = MagicMock(
        return_value=data
    )


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


class GitlabMock(object):
    """Mock GitLab API."""

    def __init__(self, server, oauth_token, email='info@hzdr.de'):
        """Init mock."""
        self.user = GLUser(email)

    def auth(self):
        """Mock auth."""
        return True
