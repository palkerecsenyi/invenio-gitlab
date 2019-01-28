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

"""Create invenio-gitlab tables."""

import uuid
from datetime import datetime

import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd3ba1d18340c'
down_revision = '22860f41f06d'
branch_labels = ()
depends_on = ('07fb52561c5c', 'a095bd179f5c', 'e12419831262')


def upgrade():
    """Upgrade database."""
    op.create_table(
        'gitlab_projects',
        sa.Column('id', sqlalchemy_utils.types.uuid.UUIDType(),
                  default=uuid.uuid4),
        sa.Column('gitlab_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('ping', sa.DateTime(), nullable=True),
        sa.Column('hook', sa.Integer()),
        sa.Column('release_pattern', sa.String(length=255), default='v*'),
        # Inherited columns from sqlalchemy_utils.models:Timestamp
        sa.Column('created', sa.DateTime(), default=datetime.utcnow,
                  nullable=False),
        sa.Column('updated', sa.DateTime(), default=datetime.utcnow,
                  nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['accounts_user.id']),
    )
    op.create_index(
        op.f('ix_gitlab_projects_gitlab_id'), 'gitlab_projects',
        ['gitlab_id'], unique=True,
    )
    op.create_index(
        op.f('ix_gitlab_projects_name'), 'gitlab_projects',
        ['name'], unique=True,
    )
    op.create_table(
        'gitlab_releases',
        sa.Column('id', sqlalchemy_utils.types.uuid.UUIDType(),
                  default=uuid.uuid4),
        sa.Column('tag', sa.String(length=255)),
        sa.Column('errors', sa.JSON().with_variant(
            sa.dialects.postgresql.JSON(none_as_null=True), 'postgresql',
        ).with_variant(
            sqlalchemy_utils.types.JSONType(), 'sqlite'
        ).with_variant(
            sqlalchemy_utils.types.JSONType(), 'mysql'
        ), nullable=True),
        sa.Column('project_id', sqlalchemy_utils.types.uuid.UUIDType()),
        sa.Column('event_id', sqlalchemy_utils.types.uuid.UUIDType(),
                  nullable=True),
        sa.Column('record_id', sqlalchemy_utils.types.uuid.UUIDType(),
                  nullable=True),
        sa.Column('status', sa.CHAR(1), nullable=False),
        # Inherited columns from sqlalchemy_utils.models:Timestamp
        sa.Column('created', sa.DateTime(), default=datetime.utcnow,
                  nullable=False),
        sa.Column('updated', sa.DateTime(), default=datetime.utcnow,
                  nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tag', 'project_id'),
        sa.ForeignKeyConstraint(['project_id'], ['gitlab_projects.id']),
        sa.ForeignKeyConstraint(['event_id'], ['webhooks_events.id']),
        sa.ForeignKeyConstraint(['record_id'], ['records_metadata.id']),
    )


def downgrade():
    """Downgrade database."""
    op.drop_index(op.f('ix_gitlab_projects_gitlab_id'),
                  table_name='gitlab_projects')
    op.drop_index(op.f('ix_gitlab_projects_name'),
                  table_name='gitlab_projects')

    op.drop_table('gitlab_releases')
    op.drop_table('gitlab_projects')
