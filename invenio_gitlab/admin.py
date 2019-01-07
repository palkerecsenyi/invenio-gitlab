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

"""Admin model views for Invenio-GitLab."""

from __future__ import absolute_import

from flask_admin.contrib.sqla import ModelView

from .models import Project, Release


def _(x):
    """Identity function for string extraction."""
    return x


class ProjectModelView(ModelView):
    """ModelView for the GitLab projects table."""

    can_create = True
    can_edit = True
    can_delete = False
    can_view_details = True
    column_display_all_relations = True
    column_list = (
        'id',
        'gitlab_id',
        'name',
        'user',
        'enabled',
        'ping',
        'hook',
    )
    column_searchable_list = ('gitlab_id', 'name', 'user.email')


class ReleaseModelView(ModelView):
    """ModelView for the GitLab Release."""

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    column_display_all_relations = True
    column_list = (
        'project',
        'tag',
        'status',
        'id',
        'release_id',
        'record_id',
        'record',
    )
    column_searchable_list = (
        'tag',
        'status',
        'project.name',
        'project.gitlab_id',
    )


project_adminview = dict(
    endpoint='gitlab_projects_admin',
    model=Project,
    modelview=ProjectModelView,
    category=_('GitLab'),
)

release_adminview = dict(
    endpoint='gitlab_releases_admin',
    model=Release,
    modelview=ReleaseModelView,
    category=_('GitLab'),
)
