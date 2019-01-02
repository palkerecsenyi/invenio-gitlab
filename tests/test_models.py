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

from invenio_gitlab.errors import InvalidRegexError, RepositoryAccessError
from invenio_gitlab.models import Repository


def test_repository(app, db, tester_id):
    """Test repositories model."""
    repository = Repository.create(
        user_id=tester_id,
        gitlab_id=1234,
        name="tester/testproject",
    )
    db.session.add(repository)
    db.session.commit()

    # get the repository by id
    repo = Repository.get(user_id=tester_id, gitlab_id=1234)
    assert repo.name == "tester/testproject"

    assert str(repo) == "<Repository tester/testproject:1234>"

    with pytest.raises(RepositoryAccessError):
        repo = Repository.get(user_id=tester_id+1, gitlab_id=1234)

    # Test creation with custom regex.
    regex = r'^v\d*\.\d*$'
    repository = Repository.create(
        user_id=tester_id,
        gitlab_id=2456,
        name="tester/testproject12",
        regex=regex,
    )
    db.session.add(repository)
    db.session.commit()

    # get the repository by id
    repo = Repository.get(user_id=tester_id, gitlab_id=2456)
    assert repo.release_regex == regex
    re.compile(repo.release_regex)

    # Test invalid regex.
    regex = r'[\d*'
    with pytest.raises(InvalidRegexError):
        repository = Repository.create(
            user_id=tester_id,
            gitlab_id=2456,
            name="tester/testproject12",
            regex=regex,
        )
