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

import base64
from datetime import datetime

import dateutil.parser
import mistune
import pytz


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


def get_description_from_readme(gl, project_id, tag):
    """Get the description content from the README file."""
    project = gl.api.projects.get(project_id)
    items = project.repository_tree(ref=tag)
    file_id = [element['id']
               for element in items if element['name'] == 'README.md'][0]
    if file_id:
        file_info = project.repository_blob(file_id)
        markdown_input = base64.b64decode(file_info['content']).decode('utf-8')
        markdown = mistune.Markdown()
        return markdown(markdown_input)
    return None
