#!/usr/bin/env python3

from github import Github
from github import Auth
from github.Label import Label


auth = Auth.Token("12345")
g = Github(base_url="http://localhost:9000", auth=auth)

for repo in g.get_repos():
    print(repo)

    #a1 = repo.create_label('a1', color='red')
    #a2 = repo.create_label('a2', color='red')

    for issue in repo.get_issues(state='all'):
        print(f'\t{issue}')

        for x in issue.get_labels():
            print(f'\t\tlabel:{x}')


        issue.add_to_labels('foobar')
        #issue.set_labels([Label('foobar'), Label('baz')])
        labels = ['foobar', 'baz']
        issue.set_labels(*labels)

        import epdb; epdb.st()
