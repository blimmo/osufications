import os
import urllib.request

with urllib.request.urlopen(os.environ.get('url')):
    pass
