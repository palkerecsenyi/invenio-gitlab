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

"""DOI badge blueprint for GitLab."""

from __future__ import absolute_import

from flask import Blueprint, abort, redirect, url_for

from ..api import GitLabRelease
from ..models import Project, ReleaseStatus

blueprint = Blueprint(
    'invenio_gitlab_badge',
    __name__,
    url_prefix='/badge/gitlab',
    static_folder='../static',
    template_folder='../templates',
)


def get_pid_of_latest_release_or_404(**kwargs):
    """Get the pid of the latest release."""
    project = Project.query.filter_by(**kwargs).first_or_404()
    release = project.latest_release(ReleaseStatus.PUBLISHED)
    if release:
        return GitLabRelease(release).pid
    abort(404)


def get_badge_image_url(pid, ext='svg'):
    """Return the badge for a DOI."""
    return url_for('invenio_formatter_badges.badge',
                   title=pid.pid_type, value=pid.pid_value, ext=ext)


def get_doi_url(pid):
    """Return the badge for a DOI."""
    return 'https://doi.org/{pid.pid_value}'.format(pid=pid)


@blueprint.route('/<int:gitlab_id>.svg')
def index(gitlab_id):
    """Generate a badge for a specific GitLab project."""
    pid = get_pid_of_latest_release_or_404(gitlab_id=gitlab_id)
    return redirect(get_badge_image_url(pid))


@blueprint.route('/latestdoi/<int:gitlab_id>')
def latest_doi(gitlab_id):
    """Redirect to the most recent record version."""
    pid = get_pid_of_latest_release_or_404(gitlab_id=gitlab_id)
    return redirect(get_doi_url(pid))
