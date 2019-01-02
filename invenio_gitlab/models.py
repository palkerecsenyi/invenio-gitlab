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

from invenio_accounts.models import User
from invenio_db import db
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import UUIDType

from .errors import InvalidRegexError, RepositoryAccessError


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

    def __repr__(self):
        """Get repository representation."""
        return u'<Repository {self.name}:{self.gitlab_id}>'.format(self=self)
