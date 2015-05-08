"""
====================
flask_flatpages.cache
====================

Define flatpage data caches.

"""

from __future__ import with_statement

import os
import errno

from pathlib import Path

from werkzeug.utils import cached_property

from . import compat
from .page import Page

class CacheBackendError(Exception):
    pass

class BaseCache(object):

    def load_page(self, page):
        raise NotImplementedError()

    def store_page(self, page):
        raise NotImplementedError()

    @property
    def root(self):
        raise NotImplementedError()

    @cached_property
    def _pages(self):
        raise NotImplementedError()


class FileCache(BaseCache):
    """
    This class is responsible to store and load the actual tile data.
    """

    def __init__(self, cache_dir, file_ext, html_renderer, encoding):
        super(FileCache, self).__init__()
        self._cache_dir = cache_dir
        self._file_ext = file_ext
        self._html_renderer = html_renderer
        self._encoding = encoding
        ensure_directory(self._cache_dir)

        self._path = Path(self._cache_dir)
        self._cache = {}


    def store_page(self, page):
        pass

    def load_page(self, page):
        mtime = page.location.stat().st_mtime
        filename = page.location.absolute()
        cached = self._cache.get(filename)

        if cached and cached[1] == mtime:
            return cached[0]

        else:
            if compat.IS_PY3:
                with page.location.open(encoding=self._encoding) as fp:
                    content = fp.read()
            else:
                with page.location.open(encoding=self._encoding) as fp:
                    content = fp.read()

            page.load_content(content)
            #self._cache[filename] == (page, mtime)

            return page

    def load_pages(self):
        if isinstance(self._file_ext, compat.string_types):
            if ',' in self._file_ext:
                ext = tuple(self._file_ext.split(','))
            else:
                ext = (self._file_ext,)
        elif isinstance(self._file_ext, (list, set)):
            ext = tuple(self._file_ext)
        else:
            raise ValueError(
                'Invalid value for FlatPages extension. Should be a string or '
                'a sequence, got {0} instead: {1}'.
                format(type(self._file_ext).__name__, self._file_ext)
            )

        pages = {}


        from pdb import set_trace
        for extension in ext:
            pattern = '**/*%s' % (extension)
            for path in self._path.glob(pattern):
                rel_path = path.relative_to(self._path)
                name = u'/'.join(rel_path.parts)
                name = name[:-len(extension)]
                page = self.load_page(Page(name, path, self._html_renderer))

                pages[name] = page

        return pages




def ensure_directory(file_name):
    """
    Create directory if it does not exist, else do nothing.
    """
    dir_name = os.path.dirname(file_name)
    if not os.path.exists(dir_name):
        try:
            os.makedirs(dir_name)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e

# def write_atomic(filename, data):
#     """
#     write_atomic writes `data` to a random file in filename's directory
#     first and renames that file to the target filename afterwards.
#     Rename is atomic on all POSIX platforms.

#     Falls back to normal write on Windows.
#     """
#     if not sys.platform.startswith('win'):
#         # write to random filename to prevent concurrent writes in cases
#         # where file locking does not work (network fs)
#         path_tmp = filename + '.tmp-' + str(random.randint(0, 99999999))
#         try:
#             fd = os.open(path_tmp, os.O_EXCL | os.O_CREAT | os.O_WRONLY)
#             with os.fdopen(fd, 'wb') as f:
#                 f.write(data)
#             os.rename(path_tmp, filename)
#         except OSError as ex:
#             try:
#                 os.unlink(path_tmp)
#             except OSError:
#                 pass
#             raise ex
#     else:
#         with open(filename, 'wb') as f:
#             f.write(data)