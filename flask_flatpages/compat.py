"""
======================
flask_flatpages.compat
======================

Compatibility module for supporting both Python 2 and Python 3.

"""

import sys


IS_PY3 = sys.version_info[0] == 3

if IS_PY3:
    string_types = (str, )  # noqa
    text_type = str  # noqa
    from io import StringIO  # noqa

else:
    string_types = (basestring, )  # noqa
    text_type = unicode  # noqa

    from StringIO import StringIO  # noqa


def itervalues(obj, **kwargs):
    """Iterate over dict values."""
    return iter(obj.values(**kwargs)) if IS_PY3 else obj.itervalues(**kwargs)
