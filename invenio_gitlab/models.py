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

"""Database models for Invenio-GitLab."""

from __future__ import absolute_import

import fnmatch
import uuid
from enum import Enum

from flask import current_app
from invenio_accounts.models import User
from invenio_db import db
from invenio_i18n import lazy_gettext as _
from invenio_records.api import Record
from invenio_records.models import RecordMetadata
from invenio_webhooks.models import Event
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import ChoiceType, JSONType, UUIDType

from .errors import (
    NoVersionTagError,
    ProjectAccessError,
    ProjectDisabledError,
    ReleaseAlreadyReceivedError,
)

RELEASE_STATUS_TITLES = {
    "RECEIVED": _("Received"),
    "PROCESSING": _("Processing"),
    "PUBLISHED": _("Published"),
    "FAILED": _("Failed"),
    "DELETED": _("Deleted"),
}

RELEASE_STATUS_ICON = {
    "RECEIVED": "fa-spinner",
    "PROCESSING": "fa-spinner",
    "PUBLISHED": "fa-check",
    "FAILED": "fa-times",
    "DELETED": "fa-times",
}

RELEASE_STATUS_COLOR = {
    "RECEIVED": "default",
    "PROCESSING": "default",
    "PUBLISHED": "success",
    "FAILED": "danger",
    "DELETED": "danger",
}


class ReleaseStatus(Enum):
    """Constants for possible status of a Release."""

    __order__ = "RECEIVED PROCESSING PUBLISHED FAILED DELETED"

    RECEIVED = "R"
    """Release has been received and is pending processing."""

    PROCESSING = "P"
    """Release is still being processed."""

    PUBLISHED = "D"
    """Release was successfully processed and published."""

    FAILED = "F"
    """Release processing has failed."""

    DELETED = "E"
    """Release has been deleted."""

    def __init__(self, value):
        """Hack."""

    def __eq__(self, other):
        """Equality test."""
        return self.value == other

    def __str__(self):
        """Return its value."""
        return self.value

    @property
    def title(self):
        """Return human readable title."""
        return RELEASE_STATUS_TITLES[self.name]

    @property
    def icon(self):
        """Font Awesome status icon."""
        return RELEASE_STATUS_ICON[self.name]

    @property
    def color(self):
        """UI status color."""
        return RELEASE_STATUS_COLOR[self.name]


class Project(db.Model, Timestamp):
    """Information about a GitLab project."""

    __tablename__ = "gitlab_projects"

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """Project identifier."""

    gitlab_id = db.Column(
        db.Integer,
        unique=True,
        index=True,
        nullable=True,
    )
    """Unique identifier for a GitLab project."""

    name = db.Column(db.String(255), unique=True, index=True, nullable=False)
    """Fully qualified name of the project including user/organization."""

    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    """Reference user that can manage this project."""

    ping = db.Column(db.DateTime, nullable=True)
    """Last ping of the project."""

    hook = db.Column(db.Integer)
    """Hook identifier."""

    release_pattern = db.Column(
        db.String(255),
        default="v*",
    )
    """Pattern to compare release tags with."""

    # Relationships
    user = db.relationship(User)

    @classmethod
    def create(cls, user_id, gitlab_id=None, name=None, pattern=None, **kwargs):
        """Create the project.

        :param int user_id: User identifier.
        :param int gitlab_id: GitLab project identifier.
        :param str name: GitLab project full name.
        :param str pattern: Glob pattern used to identify version tags.
        """
        with db.session.begin_nested():
            obj = cls(user_id=user_id, gitlab_id=gitlab_id, name=name, **kwargs)
            if pattern:
                obj.release_pattern = pattern
            db.session.add(obj)
        return obj

    @classmethod
    def get(cls, user_id, gitlab_id=None, name=None, check_owner=True):
        """Return a project.

        :param int user_id: User identifier.
        :param int gitlab_id: GitLab project identifier.
        :param str name: GitLab project full name.
        :raises: :py:exc:`~sqlalchemy.orm.exc.NoResultFound`: if the project
                 doesn't exist.
        :raises: :py:exc:`~sqlalchemy.orm.exc.MultipleResultsFound`: if
                 multiple projects with the specified GitLab id and/or name
                 exist.
        :raises: :py:exc:`~.errors.ProjectAccessError`: if the user is not the
                 owner of the project.
        """
        project = cls.query.filter(
            (Project.gitlab_id == gitlab_id) | (Project.name == name)
        ).one()
        if (
            check_owner
            and project
            and project.user_id
            and project.user_id != int(user_id)
        ):
            raise ProjectAccessError(
                "User {user} cannot access project {project}({project_id}).".format(
                    user=user_id, project=name, project_id=gitlab_id
                )
            )
        return project

    @classmethod
    def enable(cls, user_id, gitlab_id, name, hook):
        """Enable webhooks for a project."""
        try:
            project = cls.get(user_id, gitlab_id, name=name)
        except NoResultFound:
            project = cls.create(user_id=user_id, gitlab_id=gitlab_id, name=name)
        project.hook = hook
        project.user_id = user_id
        return project

    @classmethod
    def disable(cls, user_id, gitlab_id, name):
        """Disable webhooks for a repository."""
        project = cls.get(user_id, gitlab_id=gitlab_id, name=name)
        project.hook = None
        project.user_id = None
        return project

    @property
    def enabled(self):
        """Return True, if webhooks are enabled for the project."""
        return bool(self.hook)

    def latest_release(self, status=None):
        """Chronologically latest published release of the repository."""
        # Bail out fast if object not in DB session.
        if self not in db.session:
            return None
        q = self.releases if status is None else self.releases.filter_by(status=status)
        return q.order_by(db.desc(Release.created)).first()

    def __repr__(self):
        """Get project representation."""
        return "<Project {self.name}:{self.gitlab_id}>".format(self=self)


class Release(db.Model, Timestamp):
    """Information about a GitLab version tag."""

    __tablename__ = "gitlab_releases"

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """Release identifier."""

    tag = db.Column(db.String(255))
    """Release tag."""

    errors = db.Column(
        db.JSON()
        .with_variant(
            postgresql.JSON(none_as_null=True),
            "postgresql",
        )
        .with_variant(JSONType(), "sqlite")
        .with_variant(JSONType(), "mysql"),
        nullable=True,
    )
    """Release processing errors."""

    project_id = db.Column(UUIDType, db.ForeignKey(Project.id))
    """Project identifier."""

    event_id = db.Column(UUIDType, db.ForeignKey(Event.id), nullable=True)
    """Incoming webhook event identifier."""

    record_id = db.Column(
        UUIDType,
        db.ForeignKey(RecordMetadata.id),
        nullable=True,
    )
    """Record identifier."""

    status = db.Column(
        ChoiceType(ReleaseStatus, impl=db.CHAR(1)),
        nullable=False,
    )
    """Status of the release, e.g. 'processing', 'published', 'failed', etc."""

    project = db.relationship(Project, backref=db.backref("releases", lazy="dynamic"))

    recordmetadata = db.relationship(RecordMetadata, backref="gitlab_releases")
    event = db.relationship(Event)

    __table_args__ = (db.UniqueConstraint("tag", "project_id"),)
    """Only allow the same tag once per project."""

    @classmethod
    def create(cls, event):
        """Create a new release model."""
        tag = event.payload["ref"].split("refs/tags/")[1]
        # Check, if the tag matches the regular expression.
        project_id = event.payload["project_id"]
        project = Project.get(user_id=event.user_id, gitlab_id=project_id)
        if not fnmatch.fnmatchcase(tag, project.release_pattern):
            raise NoVersionTagError(
                "{tag} is not a new version tag according to the configured "
                "pattern.".format(tag=tag)
            )
        # Check, if the release has already been processed.
        existing_release = Release.query.filter_by(
            tag=tag, project_id=project.id
        ).first()
        if existing_release:
            raise ReleaseAlreadyReceivedError(
                "{release} has already been received.".format(release=existing_release)
            )

        # Create the release
        if project.enabled:
            with db.session.begin_nested():
                release = cls(
                    tag=tag,
                    project=project,
                    event=event,
                    status=ReleaseStatus.RECEIVED,
                )
                db.session.add(release)
            return release
        else:
            current_app.logger.warning(
                "Release creation attempt on disabled {project}.".format(
                    project=project
                )
            )
            raise ProjectDisabledError(
                "{project} is not enabled for webhooks.".format(project=project)
            )

    @property
    def record(self):
        """Get record object."""
        if self.recordmetadata:
            return Record(self.recordmetadata.json, model=self.recordmetadata)
        else:
            return None

    @property
    def deposit_id(self):
        """Get deposit identifier."""
        if self.record and "_deposit" in self.record:
            return self.record["_deposit"]["id"]
        else:
            return None

    def __repr__(self):
        """Get release representation."""
        return "<Release {self.tag} ({self.status.title})>".format(self=self)
