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

"""GitLab settings blueprint for Invenio."""

import humanize
from flask import Blueprint, abort, current_app, render_template, request
from flask_login import current_user, login_required
from invenio_db import db
from invenio_i18n import lazy_gettext as _
from sqlalchemy.orm.exc import NoResultFound

from ..api import GitLabAPI, GitLabRelease
from ..errors import ProjectAccessError
from ..models import Project, Release
from ..proxies import current_gitlab
from ..utils import parse_timestamp, utcnow


def create_ui_blueprint(app):
    """Creates blueprint and registers UI endpoints if the integration is enabled."""
    blueprint = Blueprint(
        "invenio_gitlab",
        __name__,
        static_folder="../static",
        template_folder="../templates",
        url_prefix="/account/settings/gitlab",
    )
    if app.config.get("GITLAB_INTEGRATION_ENABLED", False):
        with app.app_context():  # Todo: Temporary fix, it should be removed when inveniosoftware/invenio-theme#355 is merged
            register_ui_routes(blueprint)
    return blueprint


def create_api_blueprint(app):
    """Creates blueprint and registers API endpoints if the integration is enabled."""
    blueprint_api = Blueprint("invenio_gitlab_api", __name__)
    if app.config.get("GITLAB_INTEGRATION_ENABLED", False):
        register_api_routes(blueprint_api)
    return blueprint_api


def register_ui_routes(blueprint):
    @blueprint.route("/", methods=["GET", "POST"])
    @login_required
    def index():
        """Display a list of user projects."""
        gitlab = GitLabAPI(user_id=current_user.id)
        token = gitlab.session_token
        ctx = dict(connected=False)
        if token:
            # We know, the token is still valid and the user is authenticated
            if gitlab.account.extra_data.get("login") is None:
                gitlab.init_account()
                db.session.commit()

            if request.method == "POST" or gitlab.check_sync():
                # When we're in an XHR request, synchronously sync hooks
                gitlab.sync(async_hooks=(not request.is_xhr))
                db.session.commit()

            # Generate the projects view object
            extra_data = gitlab.account.extra_data
            projects = extra_data["projects"]
            if projects:
                # Enhance the projects dict, from the database model.
                db_projects = Project.query.filter(
                    Project.gitlab_id.in_([int(k) for k in projects.keys()]),
                ).all()
                for project in db_projects:
                    projects[str(project.gitlab_id)]["instance"] = project
                    projects[str(project.gitlab_id)]["latest"] = GitLabRelease(
                        project.latest_release()
                    )

            last_sync = humanize.naturaltime(
                (utcnow() - parse_timestamp(extra_data["last_sync"]))
            )

            ctx.update(
                {
                    "connected": True,
                    "projects": sorted(
                        projects.items(), key=lambda x: x[1]["full_name"]
                    ),
                    "last_sync": last_sync,
                }
            )
        return render_template(current_app.config["GITLAB_TEMPLATE_INDEX"], **ctx)

    @blueprint.route("/project/<path:name>")
    @login_required
    def project(name):
        """Display selected project."""
        user_id = current_user.id
        gitlab = GitLabAPI(user_id=user_id)
        token = gitlab.session_token
        if token:
            projects = gitlab.account.extra_data.get("projects", [])
            project = next(
                (
                    project
                    for project_id, project in projects.items()
                    if project.get("full_name") == name
                ),
                {},
            )
            if not project:
                abort(403)

            try:
                project_instance = Project.get(
                    user_id=user_id, gitlab_id=project["id"], check_owner=False
                )
            except ProjectAccessError:
                abort(403)
            except NoResultFound:
                project_instance = Project(
                    name=project["full_name"], gitlab_id=project["id"]
                )
            releases = [
                current_gitlab.release_api_class(r)
                for r in (
                    project_instance.releases.order_by(db.desc(Release.created)).all()
                    if project_instance.id
                    else []
                )
            ]
            return render_template(
                current_app.config["GITLAB_TEMPLATE_VIEW"],
                project=project_instance,
                releases=releases,
                serializer=current_gitlab.record_serializer,
            )
        abort(403)


def register_api_routes(blueprint):
    @blueprint.route("/hook", methods=["POST", "DELETE"])
    @login_required
    def hook():
        """Install or delete GitLab webhook."""
        project_id = request.json["id"]

        gitlab = GitLabAPI(user_id=current_user.id)
        projects = gitlab.account.extra_data["projects"]

        if project_id not in projects:
            abort(404)

        if request.method == "DELETE":
            try:
                if gitlab.remove_hook(project_id, projects[project_id]["full_name"]):
                    db.session.commit()
                    return "", 204
                else:
                    abort(400)
            except Exception:
                abort(403)
        elif request.method == "POST":
            try:
                if gitlab.create_hook(project_id, projects[project_id]["full_name"]):
                    db.session.commit()
                    return "", 201
                else:
                    abort(400)
            except Exception:
                abort(403)
        else:
            abort(400)

    @blueprint.route("/pattern", methods=["POST", "DELETE"])
    @login_required
    def pattern():
        """Change the pattern used for release detection."""
        project_id = request.json.get("id", None)
        if not project_id:
            abort(400, _("Specify the project ID."))

        try:
            project_instance = Project.get(
                user_id=current_user.id, gitlab_id=project_id, check_owner=True
            )
        except NoResultFound:
            abort(403)

        if request.method == "POST":
            pattern = request.json.get("pattern", None)
            if not pattern:
                abort(400, _("Specify a valid glob pattern " "for your releases."))

            project_instance.release_pattern = pattern
            db.session.commit()
            return "", 204
        elif request.method == "DELETE":
            # Reset pattern to the default value.
            project_instance.release_pattern = "v*"
            db.session.commit()
            return "", 204
