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

"""Utility functions for Invenio-GitLab."""

from __future__ import absolute_import

import base64
import json
from datetime import datetime

import dateutil.parser
import pytz
from flask import current_app

from .errors import CustomGitLabMetadataError


def utcnow():
    """UTC timestamp (with timezone)."""
    return datetime.now(tz=pytz.utc)


def iso_utcnow():
    """UTC ISO8601 formatted timestamp."""
    return utcnow().isoformat()


def parse_timestamp(x):
    """Parse ISO8601 formatted timestamp."""
    dt = dateutil.parser.parse(x)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    return dt


def get_contributors(gl, project_id):
    """Return contributors of GitLab project."""
    try:
        contributors = []
        project = gl.api.projects.get(project_id)
        for contributor in project.repository_contributors(as_list=False):
            if contributor['name']:
                contributors.append(dict(
                    name=contributor['name'],
                    affiliation='',
                ))
        return contributors
    except Exception:
        return None


def get_extra_metadata(gl, project_id, tag):
    """Extract extra metadata from the metadata file."""
    try:
        project = gl.api.projects.get(project_id)
        items = project.repository_tree(ref=tag)
        file_id = [element['id'] for element in items if element['name'] ==
                   current_app.config['GITLAB_METADATA_FILE']][0]
        if file_id:
            file_info = project.repository_blob(file_id)
            content = base64.b64decode(file_info['content'])
            if not content:
                return {}
            return json.loads(content.decode('utf-8'))
        return {}
    except ValueError:
        raise CustomGitLabMetadataError(
            u'Metadata file "{file}" is not valid JSON.'
            .format(file=current_app.config['GITHUB_METADATA_FILE'])
        )
