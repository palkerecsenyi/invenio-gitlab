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

"""Celery tasks for GitLab integration."""

from __future__ import absolute_import

import json

from celery import shared_task
from flask import current_app


@shared_task(ignore_result=True)
def process_release(release_id, verify_sender=False):
    """Process a received release from GitLab."""
    from invenio_db import db
    from invenio_rest.errors import RESTException

    from .errors import InvalidSenderError
    from .models import Release, ReleaseStatus
    from .proxies import current_gitlab

    release_model = Release.query.filter(
        Release.release_id == release_id,
        Release.status.in_([ReleaseStatus.RECEIVED, ReleaseStatus.FAILED]),
    ).one()
    release_model.status = ReleaseStatus.PROCESSING
    db.session.commit()

    release = current_gitlab.release_api_class(release_model)
    if verify_sender and not release.verify_sender():
        raise InvalidSenderError(
            u'Invalid sender for event {event} for user {user}'
            .format(event=release.event.id, user=release.event.user_id)
        )

    def _get_err_obj(msg):
        """Generate the error entry with a Sentry ID."""
        err = {'errors': msg}
        if hasattr(g, 'sentry_event_id'):
            err['error_id'] = str(g.sentry_event_id)
        return err

    try:
        release.publish()
        release.models.status = ReleaseStatus.PUBLISHED
    except RESTException as rest_ex:
        release.model.errors = json.loads(rest_ex.get_body())
        release.model.status = ReleaseStatus.FAILED
        current_app.logger.exception(
            u'Error while processing {release}'.format(release=release.model))
    except Exception:
        release.model.errors = _get_err_obj('Unknown error occured.')
        release.model.status = ReleaseStatus.FAILED
        current_app.logger.exception(
            u'Error while processing {release}'.format(release=release.model))
    finally:
        db.session.commit()
