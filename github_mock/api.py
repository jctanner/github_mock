#!/usr/bin/env python

###############################################################################
#
#   local github social auth mock
#
#       Implements just enough of github.com to supply what is needed for api
#       tests to do github social auth (no browser).
#
###############################################################################


import json
import glob
import os
import uuid
import random
import string
import sqlite3
from itertools import islice
# import requests

from flask import Flask
from flask import Response
from flask import jsonify
from flask import request
from flask import redirect
from flask import make_response
from flask import session


# app = Flask(__name__)
from github_mock import app

from .constants import DB_NAME
from .constants import UPSTREAM_PROTO
from .constants import UPSTREAM_HOST
from .constants import UPSTREAM_PORT
from .constants import UPSTREAM
from .constants import API_SERVER
from .constants import CLIENT_API_SERVER
from .constants import USERS

from .database import create_tables
from .database import get_user_by_id
from .database import get_user_by_login
from .database import get_session_by_id
from .database import set_session
from .database import get_access_token_by_id
from .database import set_access_token
from .database import delete_access_token
from .database import get_csrf_token_by_id
from .database import set_csrf_token
from .database import get_new_uid
from .database import get_new_login
from .database import get_new_password


from .data_indexer import DataIndexer


DI = DataIndexer()


def label_name_to_struct(label_name):
    return {
        'color': 'ffffff',
        'default': False,
        'description': None,
        'id': 99999999,
        'name': label_name,
        'node_id': 'XXXXXXXXXXXXXX',
        'url': None,
    }


def chunk_list(lst, chunk_size):
    """Yield successive chunks of chunk_size from lst using itertools.islice."""
    it = iter(lst)
    while True:
        chunk = list(islice(it, chunk_size))
        if not chunk:
            break
        yield chunk


def fix_urls(data):

    #print(f'fixing urls ...')

    # https://api.github.com -> http://localhost:9000
    # git@github.com: -> git@localhost:9000:

    scheme = request.scheme
    host = request.host
    newurl = scheme + '://' + host

    dtext = json.dumps(data)

    dtext = dtext.replace('https://api.github.com', newurl)
    dtext = dtext.replace('https://github.com', newurl)
    dtext = dtext.replace('git@github.com:', 'git@' + host + ':')

    return json.loads(dtext)


@app.route('/user', methods=['GET', 'POST'])
def github_user():

    # The token in the headers should allow correlation with the user this returns data about ...
    auth = request.headers['Authorization']
    print(auth)
    token = auth.split()[-1].strip()
    print(f'TOKEN: {token}')

    # fetch the token to get the uid associated
    token_data = get_access_token_by_id(token)

    # get the user via the uid
    _udata = get_user_by_id(token_data['uid'])
    username = _udata['login']
    print(username)

    # make it a one time token?
    delete_access_token(token)

    # fetch the full info about the user and drop the password
    udata = get_user_by_login(username)
    udata.pop('password', None)
    print(udata)

    return jsonify(udata)


@app.route('/repositories')
def api_repositories():

    fns = DI.get_repos()
    print(fns)

    repos = []
    for fn in fns:
        dfile = os.path.join(fn, 'data.json')
        with open(dfile, 'r') as f:
            rdata = json.loads(f.read())
        rdata = fix_urls(rdata)
        repos.append(rdata)

    repos = sorted(repos, key=lambda x: x['id'])

    return jsonify(repos)


# https://api.github.com/repos/geerlingguy/ansible-role-docker
@app.route('/repos/<orgname>/<reponame>')
def api_repo_by_path(orgname=None, reponame=None):

    fn = DI.get_repo_by_full_name(orgname + '/' + reponame)
    with open(fn, 'r') as f:
        data = json.loads(f.read())

    data = fix_urls(data)

    return jsonify(data)


# https://api.github.com/repositories/634043200/issues
@app.route('/repositories/<repoid>/issues')
def api_repositories_issues(repoid=None):
    return jsonify([])


@app.route('/repos/<orgname>/<reponame>/issues')
def api_repo_issues(orgname=None, reponame=None):

    repo_fn = DI.get_repo_by_full_name(orgname + '/' + reponame)
    repo_dn = os.path.dirname(repo_fn)
    issue_files = glob.glob(f'{repo_dn}/issues/*.json')

    issues = []
    for issue_file in issue_files:
        with open(issue_file, 'r') as f:
            idata = json.loads(f.read())
        issues.append(idata)

    state = None
    if request.args.get('state') is None:
        issues = [x for x in issues if x['state'] == 'open']
    elif request.args.get('state') == 'closed':
        issues = [x for x in issues if x['state'] == 'closed']
        state = 'closed'
    else:
        state = 'all'

    # sort: Can be one of: created, updated, comments
    if request.args.get('sort') == 'created':
        sort_key = 'crated_at'
    elif request.args.get('sort') == 'created':
        sort_key = 'updated_at'
    else:
        sort_key = 'created_at'

    if request.args.get('direction') == 'asc':
        reverse = True
    else:
        reverse = False
    issues = sorted(issues, key=lambda x: x[sort_key], reverse=reverse)

	# pagination ...
    per_page = 30
    if request.args.get('per_page'):
        try:
            _per_page = int(request.args.get('per_page'))
            if _per_page <= 100:
                per_page = _per_page
        except Exception:
            pass
    page = 0
    if request.args.get('page'):
        page = int(request.args.get('page'))
    slices = list(chunk_list(issues, per_page))
    total_count = len(issues)
    total_pages = len(slices)

    # Generate links for pagination
    links = []
    base_url = request.base_url
    common_params = f""
    if request.args.get('sort'):
        common_params += f"&sort={request.args.get('sort')}"
    if request.args.get('direction'):
        common_params += f"&direction={request.args.get('direction')}"
    if state:
        common_params += f"&state={state}"
    if page < total_pages:
        #next_url = f"{base_url}?page={page+1}&per_page={per_page}"
        next_url = f"{base_url}?page={page + 1}&per_page={per_page}{common_params}"
        links.append(f'<{next_url}>; rel="next"')
    if page > 1:
        #prev_url = f"{base_url}?page={page-1}&per_page={per_page}"
        prev_url = f"{base_url}?page={page - 1}&per_page={per_page}{common_params}"
        links.append(f'<{prev_url}>; rel="prev"')

    issues = slices[page-1]
    issues = [fix_urls(x) for x in issues]

    # Response with JSON data and headers
    response = Response(
        response=json.dumps(issues),
        status=200,
        mimetype='application/json'
    )
    if links:
        response.headers['Link'] = ', '.join(links)
    response.headers['X-Total-Count'] = total_count

    return response


# https://api.github.com/repos/modularml/mojo/issues/1
@app.route('/repos/<orgname>/<reponame>/issues/<number>')
def api_repo_issue(orgname=None, reponame=None, number=None):
    ifile = DI.get_issue_by_full_name_and_number(orgname + '/' + reponame, number)
    with open(ifile, 'r') as f:
        idata = json.loads(f.read())
    idata = fix_urls(idata)
    return jsonify(idata)


@app.route('/repos/<orgname>/<reponame>/issues/<number>/labels', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_repo_issue_labels(orgname=None, reponame=None, number=None):
    ifile = DI.get_issue_by_full_name_and_number(orgname + '/' + reponame, number)
    with open(ifile, 'r') as f:
        idata = json.loads(f.read())

    lmap = dict((x['name'], x) for x in idata['labels'])

    # POST == append
    # https://docs.github.com/en/rest/issues/labels?apiVersion=2022-11-28#add-labels-to-an-issue
    if request.method == 'POST':
        print(f'POST {request.data} {request.json}')
        for x in request.json:
            if x not in lmap:
                newlabel = label_name_to_struct(x)
                idata['labels'].append(newlabel)
        with open(ifile, 'w') as f:
            f.write(json.dumps(idata, indent=2, sort_keys=True))

    # PUT == replace
    # https://docs.github.com/en/rest/issues/labels?apiVersion=2022-11-28#set-labels-for-an-issue
    elif request.method == 'PUT':
        print(f'PUT {request.data} {request.json}')
        newlabels = []
        for x in request.json:
            if x in lmap:
                newlabels.append(lmap[x])
            else:
                newlabels.append(label_name_to_struct(x))
        idata['labels'] = newlabels
        with open(ifile, 'w') as f:
            f.write(json.dumps(idata, indent=2, sort_keys=True))

    # DELETE == clear
    elif request.method == 'DELETE':
        print(f'DELETE')
        idata['labels'] = []
        with open(ifile, 'w') as f:
            f.write(json.dumps(idata, indent=2, sort_keys=True))

    return jsonify(idata['labels'])


@app.route('/repos/<orgname>/<reponame>/issues/<number>/labels/<label>', methods=['DELETE'])
def api_repo_issue_label_delete(orgname=None, reponame=None, number=None, label=None):
    ifile = DI.get_issue_by_full_name_and_number(orgname + '/' + reponame, number)
    with open(ifile, 'r') as f:
        idata = json.loads(f.read())

    idata['labels'] = [x for x in idata['labels'] if x['name'] != label]
    with open(ifile, 'w') as f:
        f.write(json.dumps(idata, indent=2, sort_keys=True))

    return jsonify({})
