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

"""Implement OAuth client handler."""

from __future__ import absolute_import

import gitlab
from flask import current_app, redirect, url_for
from flask_login import current_user
from invenio_db import db
from invenio_oauth2server.models import Token as ProviderToken
from invenio_oauthclient.models import RemoteToken
from invenio_oauthclient.utils import oauth_link_external_id, \
    oauth_unlink_external_id
from sqlalchemy.orm.exc import NoResultFound

from .api import GitLabAPI
from .models import Project
from .tasks import disconnect_gitlab

REMOTE_APP = dict(
    title='GitLab',
    description='Integrated software development platform.',
    icon='fa fa-gitlab',
    authorized_handler='invenio_oauthclient.handlers'
                       ':authorized_signup_handler',
    disconnect_handler='invenio_gitlab.handlers:disconnect_handler',
    signup_handler=dict(
        info='invenio_gitlab.handlers:account_info',
        setup='invenio_gitlab.handlers:account_setup',
        view='invenio_oauthclient.handlers:signup_handler',
    ),
    params=dict(
        base_url='https://gitlab.com/api/v4/',
        request_token_url=None,
        access_token_url='https://gitlab.com/oauth/token',
        access_token_method='POST',
        authorize_url='https://gitlab.com/oauth/authorize',
        app_key='GITLAB_APP_CREDENTIALS',
    )
)


def account_setup(remote, token=None, response=None,
                  account_setup=None):
    """Setup user account."""
    gl = GitLabAPI(user_id=token.remote_account.user_id)
    with db.session.begin_nested():
        gl.init_account()

        oauth_link_external_id(
            token.remote_account.user,
            dict(id=str(gl.account.extra_data['id']), method='gitlab')
        )


def account_info(remote, resp):
    """Retrieve remote account information used to find local user."""
    gl = gitlab.Gitlab(
        current_app.config['GITLAB_BASE_URL'],
        oauth_token=resp['access_token'],
    )
    gl.auth()
    user_attrs = gl.user.attributes
    return dict(
        user=dict(
            email=user_attrs['email'],
            profile=dict(
                username=user_attrs['username'],
                full_name=user_attrs['name'],
            ),
        ),
        external_id=str(user_attrs['id']),
        external_method='gitlab',
    )


def disconnect_handler(remote):
    """Disconnect callback handler for GitLab."""
    if not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()

    external_method = 'gitlab'
    external_ids = [i.id for i in current_user.external_identifiers
                    if i.method == external_method]

    if external_ids:
        oauth_unlink_external_id(dict(id=external_ids[0],
                                      method=external_method))

    user_id = int(current_user.get_id())
    token = RemoteToken.get(user_id, remote.consumer_key)
    if token:
        extra_data = token.remote_account.extra_data

        # Delete the token that we issued for GitLab to deliver webhooks
        webhook_token_id = extra_data.get('tokens', {}).get('webhook')
        ProviderToken.query.filter_by(id=webhook_token_id).delete()

        # Disable GitLab webhooks from Invenio side.
        db_projects = Project.query.filter_by(user_id=user_id).all()
        projects_with_hooks = [(p.gitlab_id, p.hook)
                               for p in db_projects if p.hook]
        for project in db_projects:
            try:
                Project.disable(
                    user_id=user_id,
                    gitlab_id=project.gitlab_id,
                    name=project.name,
                )
            except NoResultFound:
                # If no project exists, just skip it, no action required
                pass
        db.session.commit()

        # Send the celery task for remote webhook removal
        disconnect_gitlab.delay(token.access_token, projects_with_hooks)

        # Delete the RemoteAccount (along with the associated RemoteToken)
        token.remote_account.delete()

    return redirect(url_for('invenio_oauthclient_settings.index'))
