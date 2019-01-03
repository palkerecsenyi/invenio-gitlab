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

import re
import uuid
from enum import Enum

from flask import current_app
from flask_babelex import lazy_gettext as _
from invenio_accounts.models import User
from invenio_db import db
from invenio_records.api import Record
from invenio_records.models import RecordMetadata
from invenio_webhooks.models import Event
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import ChoiceType, JSONType, UUIDType

from .errors import InvalidRegexError, ReleaseAlreadyReceivedError, \
    RepositoryAccessError, RepositoryDisabledError

RELEASE_STATUS_TITLES = {
    'RECEIVED': _('Received'),
    'PROCESSING': _('Processing'),
    'PUBLISHED': _('Published'),
    'FAILED': _('Failed'),
    'DELETED': _('Deleted'),
}

RELEASE_STATUS_ICON = {
    'RECEIVED': 'fa-spinner',
    'PROCESSING': 'fa-spinner',
    'PUBLISHED': 'fa-check',
    'FAILED': 'fa-times',
    'DELETED': 'fa-times',
}

RELEASE_STATUS_COLOR = {
    'RECEIVED': 'default',
    'PROCESSING': 'default',
    'PUBLISHED': 'success',
    'FAILED': 'danger',
    'DELETED': 'danger',
}


class ReleaseStatus(Enum):
    """Constants for possible status of a Release."""

    __order__ = 'RECEIVED PROCESSING PUBLISHED FAILED DELETED'

    RECEIVED = 'R'
    """Release has been received and is pending processing."""

    PROCESSING = 'P'
    """Release is still being processed."""

    PUBLISHED = 'D'
    """Release was successfully processed and published."""

    FAILED = 'F'
    """Release processing has failed."""

    DELETED = 'E'
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


class Repository(db.Model, Timestamp):
    """Information about a GitLab repository."""

    __tablename__ = 'gitlab_repositories'

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """Repository identifier."""

    gitlab_id = db.Column(
        db.Integer,
        unique=True,
        index=True,
        nullable=True,
    )
    """Unique identifier for a GitLab repository."""

    name = db.Column(db.String(255), unique=True, index=True, nullable=False)
    """Fully qualified name of the repository including user/organization."""

    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    """Reference user that can manage this repository."""

    ping = db.Column(db.DateTime, nullable=True)
    """Last ping of the repository."""

    hook = db.Column(db.Integer)
    """Hook identifier."""

    release_regex = db.Column(
        db.String(255),
        default='v.*$',
    )
    """Regex to compare release tags with."""

    # Relationships
    user = db.relationship(User)

    @classmethod
    def create(cls, user_id, gitlab_id=None, name=None, regex=None, **kwargs):
        """Create the repository."""
        with db.session.begin_nested():
            obj = cls(user_id=user_id, gitlab_id=gitlab_id, name=name,
                      **kwargs)
            if regex:
                try:
                    re.compile(regex)
                except re.error:
                    raise InvalidRegexError(
                        'Regular expression cannot be compiled.')
                obj.release_regex = regex
            db.session.add(obj)
        return obj

    @classmethod
    def get(cls, user_id, gitlab_id=None, name=None, check_owner=True):
        """Return a repository.

        :param integer user_id: User identifier.
        :param integer gitlab_id: GitLab project identifier.
        :param str name: GitLab repository full name.
        :raises: :py:exc:`~sqlalchemy.orm.exc.NoResultFound`: if the repository
                 doesn't exist.
        :raises: :py:exc:`~sqlalchemy.orm.exc.MultipleResultsFound`: if
                 multiple repositories with the specified GitLab id and/or name
                 exist.
        :raises: :py:exc:`RepositoryAccessError`: if the user is not the owner
                 of the repository.
        """
        repo = cls.query.filter((Repository.gitlab_id == gitlab_id) |
                                (Repository.name == name)).one()
        if (check_owner and repo and repo.user_id and
                repo.user_id != int(user_id)):
            raise RepositoryAccessError(
                'User {user} cannot access repository {repo}({repo_id}).'
                .format(user=user_id, repo=name, repo_id=gitlab_id)
            )
        return repo

    @classmethod
    def enable(cls, user_id, gitlab_id, name, hook):
        """Enable webhooks for a repository."""
        try:
            repo = cls.get(user_id, gitlab_id, name=name)
        except NoResultFound:
            repo = cls.create(user_id=user_id, gitlab_id=gitlab_id, name=name)
            repo.hook = hook
            repo.user_id = user_id
            return repo

    @property
    def enabled(self):
        """Return, if webhooks are enabled for the repository."""
        return bool(self.hook)

    def __repr__(self):
        """Get repository representation."""
        return u'<Repository {self.name}:{self.gitlab_id}>'.format(self=self)


class Release(db.Model, Timestamp):
    """Information about a GitLab version tag."""

    __tablename__ = 'gitlab_releases'

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """Release identifier."""

    tag = db.Column(db.String(255))
    """Release tag."""

    errors = db.Column(
        JSONType().with_variant(
            postgresql.JSON(none_as_null=True),
            'postgresql',
        ),
        nullable=True,
    )
    """Release processing errors."""

    repository_id = db.Column(UUIDType, db.ForeignKey(Repository.id))
    """Repository identifier."""

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

    repository = db.relationship(
        Repository,
        backref=db.backref('releases', lazy='dynamic')
    )

    recordmetadata = db.relationship(RecordMetadata, backref='gitlab_releases')
    event = db.relationship(Event)

    @classmethod
    def create(cls, event):
        """Create a new release model."""
        tag = event.payload['ref'].split('refs/tags/')[1]
        # Check, if the tag matches the regular expression.
        repo_id = event.payload['project_id']
        repo = Repository.get(user_id=event.user_id, gitlab_id=repo_id)
        rex = re.compile(repo.release_regex)
        if not rex.match(tag):
            return
        # Check, if the release has already been processed.
        existing_release = Release.query.filter_by(tag=tag).first()
        if existing_release:
            raise ReleaseAlreadyReceivedError(
                u'{release} has already been received.'
                .format(release=existing_release)
            )

        # Create the release
        if repo.enabled:
            with db.session.begin_nested():
                release = cls(
                    tag=tag,
                    repository=repo,
                    event=event,
                    status=ReleaseStatus.RECEIVED,
                )
                db.session.add(release)
        else:
            current_app.logger.warning(
                'Release creation attempt on disabled {repo}.'
                .format(repo=repo)
            )
            raise RepositoryDisabledError(
                '{repo} is not enabled for webhooks.'.format(repo=repo)
            )

    def __repr__(self):
        """Get release representation."""
        return (u'<Release {self.tag} ({self.status.title})>'
                .format(self=self))
