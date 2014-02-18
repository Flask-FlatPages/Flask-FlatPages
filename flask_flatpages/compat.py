"""
======================
flask_flatpages.compat
======================

Compatibility module for supporting both Python 2 and Python 3.

"""

import sys


IS_PY3 = sys.version_info[0] == 3

itervalues = lambda obj: iter(obj.values()) if IS_PY3 else obj.itervalues()
text_type = str if IS_PY3 else unicode  # noqa
