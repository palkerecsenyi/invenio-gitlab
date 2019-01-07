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

from .models import Project
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
            projects=dict(),
            last_sync=iso_utcnow(),
        )
        db.session.add(self.account)

        self.sync(hooks=False)

    def sync(self, hooks=True, async_hooks=True):
        """Synchronize user projects."""
        active_projects = {}
        # Get user owned projects.
        gitlab_projects = {project.attributes['id']: project.attributes
                           for project in self.api.projects.list(
            owned=True, simple=True)}

        for gl_project_id, gl_project in gitlab_projects.items():
            active_projects[gl_project_id] = {
                'id': gl_project_id,
                'full_name': gl_project['name_with_namespace'],
                'description': gl_project['description'],
            }

        if hooks:
            # TODO: Sync hooks here.
            pass

        # Update changed names for projects stored in DB
        db_projects = Project.query.filter(
            Project.user_id == self.user_id,
            Project.gitlab_id.in_(gitlab_projects.keys()),
        )

        for project in db_projects:
            gl_project = gitlab_projects.get(project.gitlab_id)
            if gl_project and project.name != gl_project.full_name:
                project.name = gl_project.full_name
                db.session.add(project)

        # Remove ownership from projects, that the user no longer owns,
        # or that have been deleted.
        Project.query.filter(
            Project.user_id == self.user_id,
            ~Project.gitlab_id.in_(gitlab_projects.keys())
        ).update(dict(user_id=None, hook=None), synchronize_session=False)

        # Update projects and last sync
        self.account.extra_data.update(dict(
            projects=active_projects,
            last_sync=iso_utcnow(),
        ))
        self.account.extra_data.changed()
        db.session.add(self.account)
