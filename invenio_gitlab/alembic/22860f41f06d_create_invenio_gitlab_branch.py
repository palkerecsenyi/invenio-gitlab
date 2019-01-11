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

"""Create invenio-gitlab branch."""

import sqlalchemy as sa
from alembic import op

# revision identifier used by Alembic.
revision = '22860f41f06d'
down_revision = None
branch_labels = (u'invenio_gitlab',)
depends_on = 'dbdbc1b19cf2'


def upgrade():
    """Upgrade database."""
    pass


def downgrade():
    """Downgrade database."""
    pass
