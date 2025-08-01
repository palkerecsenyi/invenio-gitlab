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

r"""
Module for Invenio that adds GitLab integration.

The Invenio-Gitlab module for Invenio adds GitLab integration to the Invenio
platform. The user links his account on the Invenio platform with its GitLab
account. This module will then gather a list of projects the user owns on
GitLab. If the user activates the preservation of releases for one of his
projects, the Invenio module registers a webhook in GitLab. This webhook is
always triggered, if a new tag is pushed to the repository. If the tag is
considered to be a version tag, the Invenio module creates a new record from
the release in GitLab.

Alembic
-------

If you wish to add the Invenio-Gitlab module to an existing installation, you
can use the provided alembic recipes to migrate your database.

In general, you need to invoke the following command to migrate your DB. Be
careful, in some situations you might need to stamp some revision first:

.. code-block:: bash

    $ invenio alembic upgrade heads

Further information is available in the documentation of
`Invenio-DB <https://invenio-db.readthedocs.io/en/latest/alembic.html>`_.

Configure the module
--------------------

Configure a custom GitLab instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Currently, the module is able to interact with one GitLab instance at a time.
By default, the module is configured to interact with https://gitlab.com. If
you want to configure a custom instance, use the following variable:


.. code-block:: python

    GITLAB_BASE_URL = 'https://gitlab.example.de'

Configure OAuth for GitLab
^^^^^^^^^^^^^^^^^^^^^^^^^^

1. *Only necessary if you do not configure for gitlab.com.* Replace
   ``gitlab.com`` with the address of the GitLab instance you want to
   configure in the below code snippet and add it to your configuration.

.. code-block:: python

    from invenio_gitlab.config import REMOTE_APP as GITLAB_REMOTE_APP

    GITLAB_REMOTE_APP['params']['base_url'] = \
        'https://gitlab.example.de/oauth/token'
    GITLAB_REMOTE_APP['params']['access_token_url'] = \
        'https://gitlab.example.de/oauth/token'
    GITLAB_REMOTE_APP['params']['access_token_url'] = \
        'https://gitlab.example.de/oauth/authorize'

2. Register the GitLab remote app in ``OAUTHCLIENT_REMOTE_APPS`` and also add
   ``GITLAB_APP_CREDENTIALS`` to your configuration:

.. code-block:: python

    from invenio_gitlab.config import REMOTE_APP as GITLAB_REMOTE_APP

    OAUTHCLIENT_REMOTE_APPS = dict(
        gitlab=GITLAB_REMOTE_APP,
    )

    GITLAB_APP_CREDENTIALS = dict(
        consumer_key='changeme',
        consumer_secret='changeme',
    )

3. Go to GitLab and register a new application:
   https://gitlab.com/profile/applications.

    3.1 Configure the redirect URI to point to:
        ``CFG_SITE_SECURE_URL/oauth/authorized/gitlab/``

    3.2 Select the ``api`` and ``read_user`` scope.

    3.3 Save the application.

.. note::  It is possible, that the administrator of your GitLab instance
           disallows users to add such applications on their own. Please
           contact your GitLab administrator on how to continue, if that is
           the case.

4. After registration, copy the *Client ID* and the *Client Secret* and add
   those to your instance configuration (``invenio.cfg``):

.. code-block:: python

    GITLAB_APP_CREDENTIALS = dict(
        consumer_key='<CLIENT ID>',
        consumer_secret='<CLIENT SECRET>',
    )

5. If everything is configured correctly, you should now be able to see GitLab
   listed under the Linked Accounts in the user settings:
   http://localhost:5000/account/settings/linkedaccounts

6. Go to ``CFG_SITE_SECURE_URL/oauth/login/gitlab/``. You should be
   redirected to GitLab and asked to permit your Invenio instance to access
   user information. (e.g. http://localhost:5000/oauth/login/gitlab/).

.. note:: Have a look into the :ref:`configuration-label` section to get a
          complete list of configuration options.

Advanced configuration
----------------------

Some Invenio instances might not want to allow sign-up/in to their instance via
GitLab. In this case you need to overwrite the default ``authorized_handler``
to only allow authenticated users to link their accounts.

.. code-block:: python

    @oauth_error_handler
    def custom_authorized_signup_handler(resp, remote, *args, **kwargs):
        # Add these lines to you custom authorized handler.
        if not current_user.is_authenticated:
            flash(_('Login via GitHub is not permitted.'), category='danger')
            return redirect('/')

        # Compare the rest of the implementation with
        # invenio_oauthclient.handlers:authorized_signup_handler

Now, you can add your custom handler to the ``GITLAB_REMOTE_APP`` in your
configuration:

.. code-block:: python

    from invenio_gitlab.config import GITLAB_REMOTE_APP

    # add this to your configuration, of course the path needs
    # to be customized to your needs
    GITLAB_REMOTE_APP['authorized_handler'] = \
        'invenio_instance.modules.gitlab.handlers' \
        ':custom_authorized_signup_handler'
"""

from __future__ import absolute_import, print_function

from .ext import InvenioGitLab

__version__ = "0.2.0"

__all__ = ("__version__", "InvenioGitLab")
