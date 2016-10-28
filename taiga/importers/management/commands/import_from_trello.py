# -*- coding: utf-8 -*-
# Copyright (C) 2014-2016 Andrey Antukh <niwi@niwi.nz>
# Copyright (C) 2014-2016 Jesús Espino <jespinog@gmail.com>
# Copyright (C) 2014-2016 David Barragán <bameda@dbarragan.com>
# Copyright (C) 2014-2016 Alejandro Alonso <alejandro.alonso@kaleidos.net>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.core.management.base import BaseCommand
from django.db.models import Q

from taiga.importers.trello import TrelloImporter
from taiga.users.models import User
from taiga.projects.services import projects as service

import unittest.mock
import timeit


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--token', dest="token", type=str,
                            help='Auth token')
        parser.add_argument('--project_id', dest="project_id", type=str,
                            help='Project ID or full name (ex: taigaio/taiga-back)')
        parser.add_argument('--template', dest='template', default="kanban",
                            help='template to use: scrum or kanban (default kanban)')
        parser.add_argument('--ask-for-users', dest='ask_for_users', const=True,
                            action="store_const", default=False,
                            help='Import closed data')
        parser.add_argument('--closed-data', dest='closed_data', const=True,
                            action="store_const", default=False,
                            help='Import closed data')

    def handle(self, *args, **options):
        admin = User.objects.get(username="admin")
        if options.get('token', None):
            token = options.get('token')
        else:
            (oauth_token, oauth_token_secret, url) = TrelloImporter.get_auth_url()
            print("Go to here and come with your token: {}".format(url))
            oauth_verifier = input("Token: ")
            access_data = TrelloImporter.get_access_token(oauth_token, oauth_token_secret, oauth_verifier)
            token = access_data['oauth_token']
        importer = TrelloImporter(admin, token)

        if options.get('project_id', None):
            project_id = options.get('project_id')
        else:
            print("Select the project to import:")
            for project in importer.list_projects():
                print("- {}: {}".format(project['id'], project['name']))
            project_id = input("Project id: ")

        users_bindings = {}
        if options.get('ask_for_users', None):
            print("Add the username or email for next trello users:")
            for user in importer.list_users(project_id):
                while True:
                    username_or_email = input("{}: ".format(user['fullName']))
                    if username_or_email == "":
                        break
                    try:
                        users_bindings[user['id']] = User.objects.get(Q(username=username_or_email) | Q(email=username_or_email))
                        break
                    except User.DoesNotExist:
                        print("ERROR: Invalid username or email")

        options = {
            "template": options.get('template'),
            "import_closed_data": options.get("closed_data", False),
            "users_bindings": users_bindings
        }
        importer.import_project(project_id, options)
