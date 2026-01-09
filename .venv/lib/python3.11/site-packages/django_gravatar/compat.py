"""
This module provides compatibility with older versions of Django and Python
"""

try:
    from urllib.parse import urlparse, parse_qs, quote_plus, urlencode
except ImportError:     # Python 2
    from urlparse import urlparse, parse_qs
    from urllib import quote_plus, urlencode

try:
    from urllib.request import Request, urlopen
except ImportError:     # Python 2
    from urllib2 import Request, urlopen

try:
    from urllib.error import HTTPError
except ImportError:     # Python 2
    from urllib2 import HTTPError

try:
    from urllib.error import URLError
except ImportError:     # Python 2
    from urllib2 import URLError
