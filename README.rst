==========
bothub-cli
==========
---------------------------
CLI tool for deploy chatbot
---------------------------

This package provides command line interface to `Bothub.studio`_ service.

Installation
============

To install bothub-cli::

  $ pip install bothub-cli

or, if you are not installing in a ``virtualenv``::

  $ sudo pip install bothub-cli

The bothub-cli package works on python2 and 3 both.


Getting Started
===============

Before using bothub-cli, you need to tell it about your `Bothub.studio`_ credentials.

.. code:: bash

   $ bothub configure
   Username: myuser
   Password: mysecret

Then it stores access token on ``~/.bothub`` directory.

To start build a new bot:

.. code:: bash

   $ mkdir mybot
   $ cd mybot
   $ bothub init
   Project name: mybot

Now you have a starter echo bot::

  .
  |-- bothub
  |   |-- bot.py
  |   `-- __init__.py
  |-- bothub.yml
  |-- requirements.txt
  `-- tests

Edit bot.py below for your purpose.

.. code:: python

   # -*- coding: utf-8 -*-

  from __future__ import (absolute_import, division, print_function, unicode_literals)

  from bothub_client.bot import BaseBot
  from bothub_client.decorators import channel

  class Bot(BaseBot):
      """Represent a Bot logic which interacts with a user.

      BaseBot superclass have methods belows:

      * Send message
        * self.send_message(message, chat_id=None, channel=None)
      * Data Storage
        * self.set_project_data(data)
        * self.get_project_data()
        * self.set_user_data(data, user_id=None, channel=None)
        * self.get_user_data(user_id=None, channel=None)
      * Channel Handler
        from bothub_client.decorators import channel
        @channel('<channel_name>')
        def channel_handler(self, event, context):
          # Handle a specific channel message
      * Command Handler
        from bothub_client.decorators import command
        @command('<command_name>')
        def command_handler(self, event, context, args):
            # Handle a command('/<command_name>')
      * Intent Handler
        from bothub_client.decorators import intent
        @intent('<intent_id>')
        def intent_result_handler(self, event, context, answers):
            # Handle a intent result
            # answers is a dict and contains intent's input data
              {
                "<intent slot id>" : <entered slot value>
                ...
              }
      """
      @channel()
      def default_handler(self, event, context):

and deploy it.

.. code:: bash

   $ bothub deploy

You also need to configure channel to use.

.. code:: bash

   $ bothub channel add telegram --api-key=<my-api-key>

Usage
=====

::

   Usage: bothub [OPTIONS] COMMAND [ARGS]...

   Bothub is a command line tool that configure, init, and deploy bot codes
   to BotHub.Studio service

   Options:
     --help  Show this message and exit.

   Commands:
     channel    Setup channels of current project
     clone      Clone existing project
     configure  Setup credentials
     deploy     Deploy project
     init       Initialize project
     logs       Show error logs
     ls         List projects
     nlu        Manage project NLU integrations
     property   Manage project properties
     rm         Delete a project
     test       Run test chat session


Setup
-----

Authorize a user and get access token.

.. code:: bash

   $ bothub configure


Project management
------------------

Initialize project on current directory. Create a echo chatbot code.

.. code:: bash

   $ bothub init

Deploy current project.

.. code:: bash

   $ bothub clone <project_name>

Clone an existing project.

.. code:: bash

   $ bothub deploy

List of projects.

.. code:: bash

   $ bothub ls

Delete a project.

.. code:: bash

   $ bothub rm <project_name>

Show error logs.

.. code:: bash

   $ bothub logs

Run current project on local machine for test.

.. code:: bash

   $ bothub test


Channel management
------------------

List of channels for current project.

.. code:: bash

   $ bothub channel ls

Add a channel for current project.

.. code:: bash

   $ bothub channel add telegram --api-key=<api_key>
   $ bothub channel add facebook --app-id=<app_id> --app-secret=<app_secret> --page-access-token=<page_access_token>

Remove a channel from current project.

.. code:: bash

   $ bothub channel rm <channel>


NLU integration managemt
------------------------

List of NLU(Natural Language Understanding) integration for current project.

.. code:: bash

   $ bothub nlu ls

Add a NLU integration for current project.

.. code:: bash

   $ bothub nlu add apiai --api-key=<api_key>

Remove a NLU integration from current project.

.. code:: bash

   $ bothub nlu rm <nlu>


License
=======

Apache License 2.0

.. _Bothub.studio: https://bothub.studio?utm_source=pypi&utm_medium=display&utm_campaign=bothub_cli
