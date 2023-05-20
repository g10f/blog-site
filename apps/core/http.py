import logging
from urllib.parse import urlsplit, urlunsplit

from django.http import QueryDict

logger = logging.getLogger(__name__)


def update_url(url, params):
    """Given a URL, add or update query parameter and return the
    modified URL.

    >>> update_url('http://example.com?foo=bar&biz=baz', {'foo': 'stuff', 'new': 'val'})
    'http://example.com?foo=stuff&biz=baz&new=val'

    """
    (scheme, netloc, path, query, fragment) = urlsplit(url)
    q = QueryDict(query, mutable=True)

    for k, v in params.items():
        if v is not None:  # filter out None values
            q[k] = v

    new_query_string = q.urlencode(safe='/')
    return urlunsplit((scheme, netloc, path, new_query_string, fragment))
