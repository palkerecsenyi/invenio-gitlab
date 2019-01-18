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

"""Test creation of badges."""

import pytest
from werkzeug.exceptions import NotFound

from invenio_gitlab.models import ReleaseStatus
from invenio_gitlab.views.badge import get_pid_of_latest_release_or_404


def test_get_pid_no_project(app, db):
    """Test get PID."""
    with pytest.raises(NotFound):
        pid = get_pid_of_latest_release_or_404()


def test_get_pid(app, db, project, release):
    """Test get PID."""
    with pytest.raises(NotFound):
        pid = get_pid_of_latest_release_or_404()
