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

"""Invenio module that adds GitLab integration to the platform."""

from __future__ import absolute_import

import gitlab
from flask import current_app
from invenio_db import db
from invenio_oauth2server.models import Token as ProviderToken
from invenio_oauthclient.models import RemoteAccount, RemoteToken
from invenio_oauthclient.proxies import current_oauthclient
from werkzeug.local import LocalProxy
from werkzeug.utils import cached_property

from .utils import iso_utcnow


class GitLabAPI(object):
    """Wrapper class for the GitLab API."""

    def __init__(self, user_id=None):
        """Create a GitLab API object."""
        self.user_id = user_id

    @cached_property
    def api(self):
        """Return an authenticated GitLab API."""
        gl = gitlab.Gitlab(
            current_app.config['GITLAB_BASE_URL'],
            oauth_token=self.access_token,
        )
        gl.auth()
        return gl

    @cached_property
    def access_token(self):
        """Return OAuth access token."""
        if self.user_id:
            return RemoteToken.get(
                self.user_id, self.remote.consumer_key
            ).access_token
        return self.remote.get_request_token()[0]

    remote = LocalProxy(
        lambda: current_oauthclient.oauth.remote_apps[
            current_app.config['GITLAB_WEBHOOK_RECEIVER_ID']
        ]
    )
    """Return OAuth remote application."""

    @cached_property
    def account(self):
        """Return the remote account."""
        return RemoteAccount.get(self.user_id, self.remote.consumer_key)

    @cached_property
    def webhook_url(self):
        """Return the url to be used by the GitLab webhook."""
        webhook_token = ProviderToken.query.filter_by(
            id=self.account.extra_data['tokens']['webhook']
        ).first()
        if webhook_token:
            webhook_url = current_app.config['GITLAB_WEBHOOK_RECEIVER_URL']
            if webhook_url:
                return webhook_url.format(token=webhook_token.access_token)
            else:
                raise RuntimeError('You must set GITLAB_WEBHOOK_RECEIVER_URL')

    def init_account(self):
        """Setup a new GitLab account."""
        gluser = self.api.user
        hook_token = ProviderToken.create_personal(
            'gitlab-webhook',
            self.user_id,
            scopes=['webhooks:event'],
            is_internal=True,
        )
        # Initial structure of extra data
        self.account.extra_data = dict(
            id=gluser.attributes['id'],
            login=gluser.attributes['username'],
            name=gluser.attributes['name'],
            tokens=dict(
                webhook=hook_token.id,
            ),
            repos=dict(),
            last_sync=iso_utcnow(),
        )
        db.session.add(self.account)

        # TODO: Sync data from Github here
