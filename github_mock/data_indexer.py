import glob
import json
import os

from pprint import pprint


class DataIndexer:
    def __init__(self):
        self.datadir = '/data'
        self.CACHE = {
            'repositories': {
                'by_id': {},
                'by_fullname': {}
            }
        }

        reposdir = os.path.join(self.datadir, 'repositories')
        for root, dirs, files in os.walk(reposdir):
            if root != reposdir:
                break
            for dirname in dirs:
                repodir = os.path.join(root, dirname)
                datafile = os.path.join(root, dirname, 'data.json')
                with open(datafile, 'r') as f:
                    repodata = json.loads(f.read())
                repoid = repodata['id']
                fullname = repodata['full_name']
                self.CACHE['repositories']['by_id'][repoid] = repodir
                self.CACHE['repositories']['by_fullname'][fullname] = repodir

        pprint(self.CACHE)

    def get_repos(self):
        return list(self.CACHE['repositories']['by_id'].values())

    def get_repo_by_full_name(self, full_name):
        return os.path.join(self.CACHE['repositories']['by_fullname'][full_name], 'data.json')
