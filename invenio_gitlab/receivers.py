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

"""Webhhok receiver implementation for Invenio-GitLab."""

from __future__ import absolute_import

from invenio_db import db
from invenio_webhooks.models import Receiver

from .errors import NoVersionTagError, ProjectAccessError, \
    ProjectDisabledError, ReleaseAlreadyReceivedError
from .models import Release
from .tasks import process_release


class GitLabReceiver(Receiver):
    """Handle incoming notification from GitLab on a new tag."""

    verify_sender = False

    def run(self, event):
        """Process an event."""
        # Handle tag event
        if event.payload['object_kind'] == "tag_push":
            try:
                release = Release.create(event)
                db.session.commit()

                process_release.delay(
                    release.tag,
                    str(release.project.id),
                    verify_sender=self.verify_sender,
                )
            except (NoVersionTagError,
                    ProjectDisabledError,
                    ReleaseAlreadyReceivedError) as e:
                event.response_code = 409
                event.response = dict(message=str(e), status=409)
            except ProjectAccessError as e:
                event.response_code = 403
                event.response = dict(message=str(e), status=403)
