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

"""GitLab settings blueprint for Invenio."""

from __future__ import absolute_import

import humanize
from flask import Blueprint, abort, current_app, render_template, request
from flask_babelex import gettext as _
from flask_breadcrumbs import register_breadcrumb
from flask_login import current_user, login_required
from flask_menu import register_menu
from invenio_db import db

from ..api import GitLabAPI, GitLabRelease
from ..models import Project
from ..utils import parse_timestamp, utcnow

blueprint = Blueprint(
    'invenio_gitlab',
    __name__,
    static_folder='../static',
    template_folder='../templates',
    url_prefix='/account/settings/gitlab',
)


#
# Views
#
@blueprint.route('/', methods=['GET', 'POST'])
@login_required
@register_menu(
    blueprint, 'settings.gitlab',
    '<i class="fa fa-gitlab fa-fw"></i> GitLab',
    order=10,
    active_when=lambda: request.endpoint.startswith('invenio_gitlab.')
)
@register_breadcrumb(blueprint, 'breadcrumbs.settings.gitlab', _('GitLab'))
def index():
    """Display a list of user projects."""
    gitlab = GitLabAPI(user_id=current_user.id)
    token = gitlab.session_token
    ctx = dict(connected=False)
    if token:
        # We know, the token is still valid and the user is authenticated
        if gitlab.account.extra_data.get('login') is None:
            gitlab.init_account()
            db.session.commit()

        if request.method == 'POST' or gitlab.check_sync():
            # When we're in an XHR request, synchronously sync hooks
            gitlab.sync(async_hooks=(not request.is_xhr))
            db.session.commit()

        # Generate the projects view object
        extra_data = gitlab.account.extra_data
        projects = extra_data['projects']
        if projects:
            # Enhance the projects dict, from the database model.
            db_projects = Project.query.filter(
                Project.gitlab_id.in_([int(k) for k in projects.keys()]),
            ).all()
            for project in db_projects:
                projects[str(project.gitlab_id)]['instance'] = project
                projects[str(project.gitlab_id)]['latest'] = GitLabRelease(
                    project.latest_release())

        last_sync = humanize.naturaltime(
            (utcnow() - parse_timestamp(extra_data['last_sync'])))

        ctx.update({
            'connected': True,
            'projects': sorted(projects.items(),
                               key=lambda x: x[1]['full_name']),
            'last_sync': last_sync,
        })
    return render_template(current_app.config['GITLAB_TEMPLATE_INDEX'], **ctx)


@blueprint.route('/hook', methods=['POST', 'DELETE'])
@login_required
def hook():
    """Install or delete GitLab webhook."""
    project_id = request.json['id']

    gitlab = GitLabAPI(user_id=current_user.id)
    projects = gitlab.account.extra_data['projects']

    if project_id not in projects:
        abort(404)

    if request.method == 'DELETE':
        try:
            if gitlab.remove_hook(project_id,
                                  projects[project_id]['full_name']):
                db.session.commit()
                return '', 204
            else:
                abort(400)
        except Exception:
            abort(403)
    elif request.method == 'POST':
        try:
            if gitlab.create_hook(project_id,
                                  projects[project_id]['full_name']):
                db.session.commit()
                return '', 201
            else:
                abort(400)
        except Exception:
            abort(403)
    else:
        abort(400)
