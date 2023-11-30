#!/usr/bin/env python

###############################################################################
#
#   local github social auth mock
#
#       Implements just enough of github.com to supply what is needed for api
#       tests to do github social auth (no browser).
#
###############################################################################


import os
import uuid
import random
import string
import sqlite3
# import requests

from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect


# for mutable users
DB_NAME = os.environ.get('DB_NAME', 'user_database.db')

# When run inside a container, we need to know how to talk to the galaxy api
UPSTREAM_PROTO = os.environ.get('UPSTREAM_PROTO')
UPSTREAM_HOST = os.environ.get('UPSTREAM_HOST')
UPSTREAM_PORT = os.environ.get('UPSTREAM_PORT')
if all([UPSTREAM_PROTO, UPSTREAM_HOST, UPSTREAM_PORT]):
    UPSTREAM = UPSTREAM_PROTO + '://' + UPSTREAM_HOST + ':' + UPSTREAM_PORT
else:
    # When this flaskapp is run on the host,
    # the api server will be available on port 5001
    UPSTREAM = 'http://localhost:5001'

# Make it simple to set the API server url or default to upstream
API_SERVER = os.environ.get('GALAXY_API_SERVER', UPSTREAM)

# How does the client talk to the API?
CLIENT_API_SERVER = os.environ.get('CLIENT_GALAXY_API_SERVER', 'http://localhost:5001')

# This is the serialized user data that github would provide
USERS = {
    'gh01': {
        'id': 1000,
        'login': 'gh01',
        'password': 'redhat',
        'email': 'gh01@gmail.com',
    },
    'gh02': {
        'id': 1001,
        'login': 'gh02',
        'password': 'redhat',
        'email': 'gh02@gmail.com',
    },
    'jctannerTEST': {
        'id': 1003,
        'login': 'jctannerTEST',
        'password': 'redhat',
        'email': 'jctannerTEST@gmail.com',
    },
    'geerlingguy': {
        'id': 481677,
        'login': 'geerlingguy',
        'password': 'redhat',
        'email': 'geerlingguy@nohaxx.me',
    }
}

OAUTH_APPS = [
    {
        'name': 'galaxy-local',
        'uid': 1000,
        'homepage': 'http://localhost:8002',
        'callback': 'http://localhost:8002/complete/github/',
        'clientid': 'Xabcd1234CLIENT',
        'secretid': 'Xabcd1234SECRET',
    }
]
