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

"""Module for Invenio that adds GitLab integration."""

from __future__ import absolute_import

from copy import deepcopy

from .handlers import REMOTE_APP

GITLAB_BASE_URL = 'https://gitlab.com'
"""Default GitLab instance to use."""

GITLAB_REMOTE_APP = deepcopy(REMOTE_APP)
"""GitLab remote application configuration."""

GITLAB_WEBHOOK_RECEIVER_URL = None
"""URL format to be used when creating a webhook in GitLab.

This variable must be set explicitly. Example:

    http://localhost:5000/api/receivers/gitlab/events/?access_token={token}

.. note::

    This config variable is used because using `url_for` to get and external
    url of an `invenio_base.api_bluebrint`, while inside the regular app
    context, doesn't work as expected.
"""

GITLAB_WEBHOOK_RECEIVER_ID = 'gitlab'
"""Local name of webhook receiver."""

GITLAB_TEMPLATE_INDEX = 'invenio_gitlab/settings/index.html'
"""GitLab settings view index template."""
