#!/usr/bin/env python

import argparse
import json
import os
import re
from datetime import datetime
from datetime import timezone

import requests
import requests_cache

from github import Auth
from github import Github
from github import Consts
from github.Requester import Requester

from logzero import logger


requests_cache.install_cache('/tmp/demo_cache')


class GithubTimeoutException(Exception):
    pass


class GithubRequesterOverride(Requester):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def requestJsonAndCheck(self, *args, retry=True, **kwargs):
        #logger.debug(f'FETCH {args[1]} {kwargs}')
        headers = {'Authorization': f'token {self.auth.token}'}
        url = args[1]
        if not url.startswith(self.base_url):
            url = self.base_url + args[1]

        if kwargs and kwargs.get('parameters'):
            params = [x for x in kwargs['parameters'].items()]
            params = ['='.join(x) for x in params]
            url += '?' + '&'.join(params)

        logger.debug(f'FETCH {url}')
        method = args[0].lower()
        func = getattr(requests, method)
        try:
            rr = func(url, headers=headers, timeout=(5, 10))
        except Exception as e:

            if not retry:
                raise GithubTimeoutException('timeout')

            if retry:
                for x in range(0, 5):
                    try:
                        headers, data = self.requestJsonAndCheck(*args, **kwargs, retry=False)
                        return headers, data
                    except GithubTimeoutException:
                        continue

                # no luck, give up
                raise Exception('github hates you')

            import epdb; epdb.st()

        #if 'issues' in url:
        #    import epdb; epdb.st()

        #return dict(rr.headers), rr.json()

        # compatibility with the pagination class requires lowercased header keys
        headers = {}
        for k,v in dict(rr.headers).items():
            headers[k.lower()] = v

        return headers, rr.json()


class GithubOverride(Github):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._Github__requester = GithubRequesterOverride(
            kwargs['auth'],
            Consts.DEFAULT_BASE_URL,
            Consts.DEFAULT_TIMEOUT,
            Consts.DEFAULT_USER_AGENT,
            Consts.DEFAULT_PER_PAGE,
            True,
            3,
            None,
            Consts.DEFAULT_SECONDS_BETWEEN_REQUESTS,
            Consts.DEFAULT_SECONDS_BETWEEN_WRITES,
        )


class GithubClient():

    def __init__(self, token=None):
        self.token = token
        auth = Auth.Token(self.token)

        #self.g = Github(auth=auth)
        #self.g.__requester = GithubRequestor(token=self.token)

        self.g = GithubOverride(auth=auth)

    def search_issues(self, query, grepo=None):
        # GET https://api.github.com/search/issues?q=commenter:foobar
        # GET https://api.github.com/search/issues?q=commenter:foobar+repo:owner/repo
        # GET https://api.github.com/search/issues?q=type:pr+reviewed-by:foobar
        # GET https://api.github.com/search/issues?q=type:pr+reviewed-by:foobar+repo:owner/repo

        next_url = 'https://api.github.com/search/issues?q=' + query
        while next_url:
            logger.info(f'FETCH {next_url}')
            rr = requests.get(next_url, headers={'Authorization': f'token {self.token}'})
            items = rr.json()['items']
            for item in items:
                number = item['number']
                yield grepo.get_issue(number)

            if not rr.headers.get('Link'):
                break
            links = rr.headers.get('Link')
            if 'next' not in rr.links:
                break
            next_url = rr.links['next']['url']

    def get_repository(self, path):
        repo = self.g.get_repo(path)
        if repo is None:
            import epdb; epdb.st()
        return repo

        for x in self.g.search_repositories(path):
            if x.full_name == path:
                return x



def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--dest', default='/data')
    args = parser.parse_args()

    token = os.environ.get('GITHUB_TOKEN')
    gc = GithubClient(token=token)

    # define the projects
    repos = [
        'geerlingguy/ansible-role-docker',
        'geerlingguy/ansible-role-php',
        'meta-llama/llama3',
        'OpenDevin/OpenDevin',
        'modularml/mojo'
    ]

    for repo_fullname in repos:
        print(repo_fullname)
        repo = gc.get_repository(repo_fullname)
        #import epdb; epdb.st()

        # where to put all the stuff for this repo ...
        repo_dir = os.path.join(args.dest, 'repositories', str(repo.id))
        if not os.path.exists(repo_dir):
            os.makedirs(repo_dir)

        # write out the repo's information ...
        with open(os.path.join(repo_dir, 'data.json'), 'w') as f:
            f.write(json.dumps(repo.raw_data, indent=2, sort_keys=True))

        # make a path for the issues
        idir = os.path.join(repo_dir, 'issues')
        if not os.path.exists(idir):
            os.makedirs(idir)

        # fetch and store all the issues ...
        for issue in repo.get_issues(state='all', sort='created_at'):
            print(issue)
            rd = issue.raw_data
            ifile = os.path.join(idir, str(issue.id) + '.' + str(issue.number) + '.json')
            with open(ifile, 'w') as f:
                f.write(json.dumps(rd, indent=2, sort_keys=True))
            #import epdb; epdb.st()

        #import epdb; epdb.st()

    import epdb; epdb.st()


if __name__ == "__main__":
    main()
