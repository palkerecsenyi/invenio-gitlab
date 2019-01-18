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

"""Test the webhhooks."""

import json

from invenio_webhooks.models import Event

from invenio_gitlab.models import Project, Release


def test_webhook_post(app, db, tester_id, hook_response):
    """Test payload treatmend on the webhook."""
    Project.enable(tester_id, gitlab_id=1234, name="Example", hook=456)
    db.session.commit()

    headers = [('Content-Type', 'application/json')]
    with app.test_request_context(headers=headers,
                                  data=json.dumps(hook_response)):
        # Create successful event.
        event = Event.create(receiver_id='gitlab', user_id=tester_id)
        db.session.commit()
        event.process()
        db.session.commit()
        assert event.response_code == 202

    assert Release.query.count() == 1

    # Send webhook a second time and expect 409
    with app.test_request_context(headers=headers,
                                  data=json.dumps(hook_response)):
        event = Event.create(receiver_id='gitlab', user_id=tester_id)
        db.session.commit()
        event.process()
        db.session.commit()
        assert event.response_code == 409

    assert Release.query.count() == 1
