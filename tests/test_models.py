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

import fnmatch
import uuid

import pytest
from invenio_webhooks.models import Event

from invenio_gitlab.errors import NoVersionTagError, ProjectAccessError, \
    ProjectDisabledError, ReleaseAlreadyReceivedError
from invenio_gitlab.models import Project, Release


def test_project(app, db, tester_id):
    """Test projects model."""
    project = Project.create(
        user_id=tester_id,
        gitlab_id=1234,
        name='tester/testproject',
    )
    db.session.add(project)
    db.session.commit()

    # get the project by id
    project = Project.get(user_id=tester_id, gitlab_id=1234)
    assert project.name == 'tester/testproject'

    assert str(project) == '<Project tester/testproject:1234>'

    with pytest.raises(ProjectAccessError):
        project = Project.get(user_id=tester_id+1, gitlab_id=1234)

    # Test creation with custom pattern.
    pattern = 'v[0-9].[0-9].[0-9]'
    project = Project.create(
        user_id=tester_id,
        gitlab_id=2456,
        name='tester/testproject12',
        pattern=pattern,
    )
    db.session.add(project)
    db.session.commit()

    # get the project by id
    project = Project.get(user_id=tester_id, gitlab_id=2456)
    assert project.release_pattern == pattern

    # Test project enabling
    project = Project.enable(
        user_id=tester_id,
        gitlab_id=2456,
        name='tester/testproject12',
        hook=12345,
    )
    db.session.commit()

    # get the project by id
    project = Project.get(user_id=tester_id, gitlab_id=2456)
    assert project.enabled
    assert project.hook == 12345

    # Disable project
    project = Project.disable(
        user_id=tester_id,
        gitlab_id=2456,
        name='tester/testproject12',
    )
    db.session.commit()

    # get the project by id
    project = Project.get(user_id=tester_id, gitlab_id=2456)
    assert not project.enabled
    assert not project.hook

    # Test project with no releases
    assert not project.latest_release()


def test_release(app, db, project, user, event, hook_response):
    """Test the release model."""
    release = Release.create(event)
    db.session.commit()
    assert release.project_id == project.id
    assert release.tag == 'v1.0.0'

    # Test double receive receipt
    with pytest.raises(ReleaseAlreadyReceivedError):
        release = Release.create(event)

    # delete release
    db.session.delete(release)

    # Release creation on disabled project
    with pytest.raises(ProjectDisabledError):
        project.disable(user.id, 1234, 'test/test')
        db.session.commit()
        release = Release.create(event)

    # Test with event not fitting pattern
    hook_response['ref'] = 'refs/tags/test'
    event = Event(
        id=uuid.uuid4(),
        receiver_id='gitlab',
        user_id=user.id,
        payload=hook_response,
        payload_headers={},
        response_headers={},
    )
    db.session.add(event)
    db.session.commit()

    with pytest.raises(NoVersionTagError):
        release = Release.create(event)
