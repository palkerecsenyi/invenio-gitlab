# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2019 HZDR
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

import os

from setuptools import find_packages, setup

readme = open('README.rst').read()
history = open('CHANGES.rst').read()

tests_require = [
    'check-manifest>=0.25',
    'coverage>=4.0',
    'invenio-userprofiles>=1.0.0',
    'isort>=4.3.3',
    'mock>=1.3.0',
    'pydocstyle>=1.0.0',
    'pytest-cache>=1.0',
    'pytest-cov>=1.8.0',
    'pytest-pep8>=1.0.6',
    'pytest>=3.7.0',
]

extras_require = {
    'docs': [
        'Sphinx>=1.5.1',
    ],
    'mysql': [
        'invenio-db[mysql,versioning]>=1.0.0',
    ],
    'postgresql': [
        'invenio-db[postgresql,versioning]>=1.0.0',
    ],
    'sqlite': [
        'invenio-db[versioning]>=1.0.0',
    ],
    'tests': tests_require,
}

extras_require['all'] = []
for name, reqs in extras_require.items():
    if name in ('mysql', 'postgresql', 'sqlite'):
        continue
    extras_require['all'].extend(reqs)

setup_requires = [
    'Babel>=1.3',
    'pytest-runner>=2.6.2',
]

install_requires = [
    'Flask>=0.11.1',
    'Flask-BabelEx>=0.9.2',
    'Flask-OAuthlib>=0.9.3',
    'humanize>=0.5.1',
    'invenio-accounts>=1.0.0',
    'invenio-assets>=1.0.0',
    'invenio-celery>=1.0.0',
    'invenio-deposit>=1.0.0a9',
    'invenio-oauthclient>=1.0.0',
    'invenio-oauth2server>=1.0.0',
    'invenio-pidstore>=1.0.0',
    'invenio-records>=1.0.0',
    'invenio-webhooks>=1.0.0a4',
    'python-gitlab>=1.7.0',
]

packages = find_packages()


# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join('invenio_gitlab', 'version.py'), 'rt') as fp:
    exec(fp.read(), g)
    version = g['__version__']

setup(
    name='invenio-gitlab',
    version=version,
    description=__doc__,
    long_description=readme + '\n\n' + history,
    keywords='invenio gitlab softwarecitation reproducibility',
    license='GPLv3',
    author='HZDR',
    author_email='fwcc@hzdr.de',
    url='https://gitlab.hzdr.de/rodare/invenio-gitlab',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'invenio_base.apps': [
            'invenio_gitlab = invenio_gitlab:InvenioGitLab',
        ],
        'invenio_base.blueprints': [
            'invenio_gitlab_settings = invenio_gitlab.views.gitlab:blueprint',
        ],
        'invenio_i18n.translations': [
            'messages = invenio_gitlab',
        ],
        'invenio_celery.tasks': [
            'invenio_gitlab = invenio_gitlab.tasks',
        ],
        'invenio_db.models': [
            'invenio_gitlab = invenio_gitlab.models',
        ],
        'invenio_webhooks.receivers': [
            'gitlab = invenio_gitlab.receivers:GitLabReceiver',
        ],
        'invenio_admin.views': [
            'invenio_gitlab_project = '
            'invenio_gitlab.admin:project_adminview',
            'invenio_gitlab_releases = '
            'invenio_gitlab.admin:release_adminview',
        ],
        'invenio_assets.bundles': [
            'invenio_gitlab_js = invenio_gitlab.bundles:js',
            'invenio_gitlab_css = invenio_gitlab.bundles:css',
        ],
    },
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Development Status :: 1 - Planning',
    ],
)
