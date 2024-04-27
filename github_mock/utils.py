import json


def fix_urls(data, request):

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

