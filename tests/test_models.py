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

"""Test DB models."""

import re

import pytest

from invenio_gitlab.errors import InvalidRegexError, ProjectAccessError
from invenio_gitlab.models import Project


def test_project(app, db, tester_id):
    """Test projects model."""
    project = Project.create(
        user_id=tester_id,
        gitlab_id=1234,
        name="tester/testproject",
    )
    db.session.add(project)
    db.session.commit()

    # get the project by id
    project = Project.get(user_id=tester_id, gitlab_id=1234)
    assert project.name == "tester/testproject"

    assert str(project) == "<Project tester/testproject:1234>"

    with pytest.raises(ProjectAccessError):
        project = Project.get(user_id=tester_id+1, gitlab_id=1234)

    # Test creation with custom regex.
    regex = r'^v\d*\.\d*$'
    project = Project.create(
        user_id=tester_id,
        gitlab_id=2456,
        name="tester/testproject12",
        regex=regex,
    )
    db.session.add(project)
    db.session.commit()

    # get the project by id
    project = Project.get(user_id=tester_id, gitlab_id=2456)
    assert project.release_regex == regex
    re.compile(project.release_regex)

    # Test invalid regex.
    regex = r'[\d*'
    with pytest.raises(InvalidRegexError):
        project = Project.create(
            user_id=tester_id,
            gitlab_id=2456,
            name="tester/testproject12",
            regex=regex,
        )
