# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function, unicode_literals)

import os
import sys
import json
import time
import traceback
import yaml

from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory

from bothub_client.clients import NluClientFactory

from bothub_cli import exceptions as exc
from bothub_cli.api import Api
from bothub_cli.config import Config
from bothub_cli.config import ProjectConfig
from bothub_cli.config import ProjectMeta
from bothub_cli.config import ProjectProperty
from bothub_cli.clients import ConsoleChannelClient
from bothub_cli.clients import CachedStorageClient
from bothub_cli.clients import ExternalHttpStorageClient
from bothub_cli.utils import safe_mkdir
from bothub_cli.utils import read_content_from_file
from bothub_cli.utils import make_dist_package
from bothub_cli.utils import extract_dist_package
from bothub_cli.utils import make_event
from bothub_cli.utils import tabulate_dict
from bothub_cli.utils import get_bot_class


class Cli(object):
    '''A CLI class represents '''
    def __init__(self, api=None, config=None, project_config=None, project_meta=None, project_property=None, print_error=None, print_message=None):
        self.api = api or Api()
        self.config = config or Config()
        self.project_config = project_config or ProjectConfig()
        self.project_meta = project_meta or ProjectMeta()
        self.project_property = project_property or ProjectProperty()
        if not self.project_meta.is_exists() and self.project_config.is_exists():
            self.project_config.load()
            self.project_meta.migrate_from_project_config(self.project_config)

        self.print_error = print_error or print
        self.print_message = print_message or print

    def authenticate(self, username, password):
        token = self.api.authenticate(username, password)
        self.config.set('auth_token', token)
        self.config.save()

    def init(self, name, description):
        self._load_auth()
        project = self.api.create_project(name, description)
        project_id = project['id']
        programming_language = 'python3'
        self.project_meta.set('id', project_id)
        self.project_meta.set('name', name)
        self.project_meta.save()
        self.project_property.config = {}
        self.project_property.save()

        self.project_config.set('programming-language', programming_language)
        self.project_config.save()

    def init_code(self):
        project_id = self.project_meta.get('id')
        programming_language = self.project_config.get('programming-language')
        self.api.upload_code(project_id, programming_language)

    def get_project(self, project_id):
        self._load_auth()
        return self.api.get_project(project_id)

    def ls(self, verbose=False):
        self._load_auth()
        projects = self.api.list_projects()
        args = ('name',) if not verbose else ('name', 'status', 'regdate')
        result = tabulate_dict(projects, *args)
        return result

    def rm(self, name):
        self._load_auth()
        projects = self.api.list_projects()
        _projects = [p for p in projects if p['name'] == name]
        if not _projects:
            raise exc.ProjectNameNotFound(name)
        for project in _projects:
            self.api.delete_project(project['id'])

    def deploy(self, console=None, source_dir='.', max_retries=30):
        self._load_auth()
        self.project_config.load()

        safe_mkdir('dist')
        dist_file_path = os.path.join('dist', 'bot.tgz')
        if console:
            console('Make dist package.')
        make_dist_package(dist_file_path, source_dir)

        if console:
            console('Upload code', nl=False)
        with open(dist_file_path, 'rb') as dist_file:
            dependency = read_content_from_file('requirements.txt') or 'bothub'
            project_id = self._get_current_project_id()
            self.api.upload_code(
                project_id,
                self.project_config.get('programming-language'),
                dist_file,
                dependency
            )
        self._wait_deploy_completion(project_id, console, max_retries=max_retries)

    def clone(self, project_name, target_dir=None):
        _target_dir = target_dir or project_name

        if os.path.isdir(_target_dir) and _target_dir != '.':
            raise exc.TargetDirectoryDuplicated(_target_dir)

        self._load_auth()
        project_id = self._get_project_id_with_name(project_name)
        self.project_meta.set('id', project_id)
        self.project_meta.set('name', project_name)
        self.project_meta.save(_target_dir)
        response = self.api.get_code(project_id)
        code = response['code']
        code_byte = eval(code) if code[0] == 'b' else code

        with open('code.tgz', 'wb') as code_file:
            code_file.write(code_byte)

        extract_dist_package('code.tgz', _target_dir)
        if os.path.isfile('code.tgz'):
            os.remove('code.tgz')

    def add_channel(self, channel, credentials):
        self._load_auth()
        project_id = self._get_current_project_id()
        self.api.add_project_channel(project_id, channel, credentials)

    def ls_channel(self, verbose=False):
        self._load_auth()
        project_id = self._get_current_project_id()
        channels = self.api.get_project_channels(project_id)
        args = ('channel',) if not verbose else ('channel', 'credentials')
        result = tabulate_dict(channels, *args)
        return result

    def rm_channel(self, channel):
        self._load_auth()
        project_id = self._get_current_project_id()
        self.api.delete_project_channels(project_id, channel)

    def ls_properties(self):
        self.project_property.load()
        return self.project_property.config

    def reload_properties(self):
        self._load_auth()
        project_id = self._get_current_project_id()
        properties = self.api.get_project_property(project_id)
        if not properties:
            self.project_property.config = {}
            self.project_property.save()
        for k in properties:
            self.project_property.set(k,properties[k])
            self.project_property.save()
        return properties

    def get_properties(self, key):
        self.project_property.load()
        return self.project_property.config[key]

    def set_properties(self, key, value):
        try:
            _value = json.loads(value)
        except ValueError:
            _value = value

        self.project_property.load()
        self.project_property.set(key,value)
        self.project_property.save()

        self._load_auth()
        project_id = self._get_current_project_id()
        return self.api.set_project_property(project_id, key, _value)

    def rm_properties(self, key):
        self._load_auth()
        self.project_property.load()
        if self.project_property.config.get(key):
            self.project_property.__delitem__(key)
            self.project_property.save()
        project_id = self._get_current_project_id()
        self.api.delete_project_property(project_id, key)

    def read_property_file(self, file):
        try:
            return yaml.load(file)
        except:
            raise exc.InvalidJsonFormat()

    def show_help(self):
        self.print_message()
        self.print_message("Bothub Test Console")
        self.print_message("-------------------")
        self.print_message()
        self.print_message("Commands:")
        self.print_message()
        commands = [
            ("help", "Print help menu"),
            ("location", "Send user location"),
            ("updateproperties", "Update local project properties from server"),
            ("exit", "Exit the Test console"),
        ]
        max_len = max([len(command) for command, _ in commands])
        template_string = "  /{0}{2}{1}"
        for command, description in commands:
            nSpace = (max_len - len(command)) + 2 # 2 is extra spaces
            width = ' ' * nSpace
            self.print_message(template_string.format(command, description, width))
        self.print_message()

    def test(self):
        self._load_auth()
        history = FileHistory('.history')

        project_id = self._get_current_project_id()
        bot_meta = self._load_bot()
        bot = bot_meta['bot']
        storage_client = bot_meta['storage_client'] # type: CachedStorageClient
        self.show_help()
        storage_client.load_project_data()
        while True:
            try:
                line = prompt('BotHub> ', history=history)
                if not line:
                    continue
                if line.startswith('/help'):
                    self.show_help()
                elif line.startswith('/updateproperties'):
                    storage_client.load_project_data()
                elif line.startswith('/exit'):
                    break
                else:
                    event = make_event(line)
                    context = {}
                    bot.handle_message(event, context)
            except (EOFError, KeyboardInterrupt):
                break
            except Exception:
                traceback.print_exc()
        storage_client.store_project_data()

    def add_nlu(self, nlu, credentials):
        self._load_auth()
        project_id = self._get_current_project_id()
        self.api.add_project_nlu(project_id, nlu, credentials)

    def ls_nlus(self, verbose=False):
        self._load_auth()
        project_id = self._get_current_project_id()
        nlus = self.api.get_project_nlus(project_id)
        args = ('nlu',) if not verbose else ('nlu', 'credentials')
        result = tabulate_dict(nlus, *args)
        return result

    def rm_nlu(self, nlu):
        self._load_auth()
        project_id = self._get_current_project_id()
        self.api.delete_project_nlu(project_id, nlu)

    def logs(self):
        self._load_auth()
        project_id = self._get_current_project_id()
        logs = self.api.get_project_execution_logs(project_id)
        return sorted(logs, key=lambda x: x['regdate'])

    def _load_auth(self):
        '''Load auth token from bothub config and inject to API class'''
        self.config.load()
        self.api.load_auth(self.config)

    def _get_current_project_id(self):
        self.project_meta.load()
        project_id = self.project_meta.get('id')
        if not project_id:
            raise exc.ImproperlyConfigured()
        return project_id

    def _get_project_id_with_name(self, project_name):
        self._load_auth()
        projects = self.api.list_projects()
        for p in projects:
            if p['name'] == project_name:
                return p['id']
        raise exc.ProjectNameNotFound(project_name)

    def _wait_deploy_completion(self, project_id, console, wait_interval=1, max_retries=30):
        first_deploying_dot = True
        for _ in range(max_retries):
            project = self.api.get_project(project_id)
            if project['status'] == 'online':
                if console:
                    console('.')
                return

            if project['status'] == 'deploying' and console:
                if first_deploying_dot:
                    console('.')
                    console('Restarting container', nl=False)
                    first_deploying_dot = False

            if console:
                console('.', nl=False)
            time.sleep(wait_interval)
        raise exc.DeployFailed()

    def _load_bot(self, target_dir='.'):
        project_id = self._get_current_project_id()
        event = {
            'sender': {
                'id': '-1'
            },
            'channel': 'console'
        }
        context = {}
        nlus = self.api.get_project_nlus(project_id)
        context['nlu'] = dict([(nlu['nlu'], nlu['credentials']) for nlu in nlus])

        channel_client = ConsoleChannelClient()
        http_storage_client = ExternalHttpStorageClient(
            self.config.get('auth_token'),
            project_id,
        )
        storage_client = CachedStorageClient(http_storage_client)
        nlu_client_factory = NluClientFactory(context)
        bot_class = get_bot_class(target_dir)
        bot = bot_class(
            channel_client=channel_client,
            storage_client=storage_client,
            nlu_client_factory=nlu_client_factory,
            event=event
        )
        return {'bot': bot, 'channel_client': channel_client, 'storage_client': storage_client,
                'nlu_client_factory': nlu_client_factory}
