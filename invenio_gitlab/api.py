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
from invenio_oauthclient.handlers import token_getter
from invenio_oauthclient.models import RemoteAccount, RemoteToken
from invenio_oauthclient.proxies import current_oauthclient
from six import string_types
from werkzeug.local import LocalProxy
from werkzeug.utils import cached_property, import_string

from .models import Project
from .utils import iso_utcnow, parse_timestamp, utcnow


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

    @property
    def session_token(self):
        """Return OAuth session token."""
        session_token = None
        if self.user_id is not None:
            session_token = token_getter(self.remote)
        if session_token:
            token = RemoteToken.get(
                self.user_id, self.remote.consumer_key,
                access_token=session_token[0]
            )
            return token
        return None

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
                'full_name': gl_project['path_with_namespace'],
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
            if (gl_project and
                    project.name != gl_project['path_with_namespace']):
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

    def check_sync(self):
        """Check if sync is required based on the last sync date."""
        # If no refresh interval is given, refresh every time.
        expiration = utcnow()
        refresh_td = current_app.config.get('GITLAB_REFRESH_TIMEDELTA')
        if refresh_td:
            expiration -= refresh_td
        last_sync = parse_timestamp(self.account.extra_data['last_sync'])
        return last_sync < expiration

    def create_hook(self, project_id, project_name):
        """Create project webhook."""
        attributes = {
            'url': self.webhook_url,
            'push_events': 0,
            'tag_push_events': 1,
            'token': current_app.config['GITLAB_SHARED_SECRET'],
            'enable_ssl_verification': 1 if not current_app.config[
                'GITLAB_INSECURE_SSL'] else 0,
        }
        gl_project = self.api.projects.get(project_id)
        if gl_project:
            try:
                # Check, if hook is already installed.
                hooks = (h for h in gl_project.hooks.list()
                         if h.attributes.get('url', '') == attributes['url'])
                for h in hooks:
                    h.delete()
                # Recreate the webhook.
                hook = gl_project.hooks.create(attributes)
            except gitlab.GitlabError:
                current_app.logger.error('Could not create webhook.')
            finally:
                if hook:
                    Project.enable(
                        user_id=self.user_id,
                        gitlab_id=project_id,
                        name=project_name,
                        hook=hook.id,
                    )
                    return True
        return False

    def remove_hook(self, project_id, name):
        """Remove webook from GitLab project."""
        gl_project = self.api.projects.get(project_id)
        if gl_project:
            # Check, if hook is installed.
            hooks = (h for h in gl_project.hooks.list()
                     if h.attributes.get('url', '') == self.webhook_url)
            for h in hooks:
                h.delete()
            Project.disable(
                user_id=self.user_id,
                gitlab_id=project_id,
                name=name,
            )
            return True
        return False


class GitLabRelease(object):
    """A GitLab release."""

    def __init__(self, release):
        """Init GitLab release."""
        self.model = release

    @cached_property
    def gl(self):
        """Return GitLab API object."""
        return GitLabAPI(user_id=self.event.user_id)

    @cached_property
    def deposit_class(self):
        """Return a class implementing the `publish` method."""
        cls = current_app.config['GITLAB_DEPOSIT_CLASS']
        if isinstance(cls, string_types):
            cls = import_string(cls)
        assert isinstance(cls, type)
        return cls

    @cached_property
    def event(self):
        """Get the release event."""
        return self.model.event

    @cached_property
    def payload(self):
        """Return release metadata."""
        return self.event.payload

    @cached_property
    def tag(self):
        """Return tag metadata."""
        project = self.gl.api.projects.get(self.payload['project_id'])
        tag = project.tags.get(self.payload['ref'].split('refs/tags/')[1])
        return tag.attributes

    @cached_property
    def commit_sha(self):
        """Return commit sha of the current release."""
        return self.event.payload['checkout_sha']

    @cached_property
    def project(self):
        """Return project metadata."""
        return self.event.payload['project']

    @cached_property
    def title(self):
        """Extract title from a release."""
        if self.event:
            if (self.project['name']
                    not in self.project['path_with_namespace']):
                return u'{0}: {1}'.format(
                    self.project['path_with_namespace'], self.project['name']
                )
        return u'{0}: {1}'.format(self.project['path_with_namespace'],
                                  self.tag['name'])

    @cached_property
    def description(self):
        """Return project description."""
        return self.project['description']

    @cached_property
    def related_identifiers(self):
        """Yield releated identifiers."""
        yield dict(
            identifier=u'{0}/tree/{1}'.format(
                self.project['web_url'], self.tag['name']
            ),
            relation='isSupplementTo',
        )

    @cached_property
    def defaults(self):
        """Return default metadata."""
        return dict(
            access_right='open',
            title=self.title,
            description=self.description,
            license='other-open',
            publication_date=self.tag['commit']['created_at'][:10],
            related_identifiers=list(self.related_identifiers),
            version=self.tag['name'],
            upload_type='software',
        )

    @cached_property
    def filename(self):
        """Extract files to download from the GitLab payload."""
        tag_name = self.event.payload['ref'].split('refs/tags/')[1]
        project_name = self.project['path_with_namespace']

        filename = u'{name}-{tag}.tar.gz'.format(
            name=project_name, tag=tag_name)

        return filename

    @property
    def metadata(self):
        """Return extracted metadata."""
        output = dict(self.defaults)
        # TODO: update metadata with additional metadata here
        return output

    @cached_property
    def status(self):
        """Return the release status of the model."""
        return self.model.status

    def publish(self):
        """Publish GitLab release as a record."""
        with db.session.begin_nested():
            deposit = self.deposit_class.create(self.metadata)
            deposit['_deposit']['created_by'] = self.event.user_id
            deposit['_deposit']['owners'] = [self.event.user_id]

            # Fetch the deposit files
            project = self.gl.api.projects.get(self.payload['project_id'])
            deposit.files[self.filename] = project.repository_archive(
                sha=self.commit_sha,
                streamed=True,
            )

            deposit.publish()
            recid, record = deposit.fetch_published()
            self.model.recordmetadata = record.model
