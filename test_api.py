#!/usr/bin/env python3

from github import Github
from github import Auth


auth = Auth.Token("12345")
g = Github(base_url="http://localhost:9000", auth=auth)

for repo in g.get_repos():
    print(repo)

    for issue in repo.get_issues(state='all'):
        print(f'\t{issue}')
    #import epdb; epdb.st()
