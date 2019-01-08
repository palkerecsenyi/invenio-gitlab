# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 HZDR
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

"""Module for Invenio that adds GitLab integration."""

from __future__ import absolute_import, print_function

from . import config


class InvenioGitLab(object):
    """Invenio-GitLab extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        app.extensions['invenio-gitlab'] = self

    def init_config(self, app):
        """Initialize configuration."""
        app.config.setdefault(
            'GITLAB_BASE_TEMPLATE',
            app.config.get('BASE_TEMPLATE',
                           'invenio_gitlab/base.html'))
        app.config.setdefault(
            'GITLAB_SETTINGS_TEMPLATE',
            app.config.get('SETTINGS_TEMPLATE',
                           'invenio_gitlab/settings/base.html'))
        for k in dir(config):
            if k.startswith('GITLAB_'):
                app.config.setdefault(k, getattr(config, k))
