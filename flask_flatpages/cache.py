"""
====================
flask_flatpages.cache
====================

Define flatpage data caches.

"""

from __future__ import with_statement

import sqlite3
import threading
import time
import unicodedata

from pathlib import Path

from . import compat
from .page import Page
from .utils import ensure_directory


class BaseCache(object):

    """Base class for all caches.

    Each cache should support the methods to load, store and delete a page from
    the cache.
    """

    def __init__(self, cache_path):
        """Create a persistent cache in the filesystem at the given path."""
        self._root = Path(cache_path).absolute()
        self._cache = {}

    def load_page(self, page):
        """Load a page from the cache.

        This method needs to be reimplemented by child classes.
        """
        raise NotImplementedError()

    def load_pages(self, html_renderer):
        """Load all pages from the cache.

        This method needs to be reimplemented by child classes.
        """
        raise NotImplementedError()

    def store_page(self, page):
        """Store a page in the cache.

        This method needs to be reimplemented by child classes.
        """
        raise NotImplementedError()

    def delete_page(self, page):
        """Delete a page from the cache.

        This method needs to be reimplemented by child classes.
        """
        raise NotImplementedError()

    def empty(self):
        """Delete the memory cache."""
        self._cache = {}


class FileCache(BaseCache):

    """A file cache, which stores :class:`Page` objects in the file sytem."""

    def __init__(self, cache_dir, file_ext, encoding):
        """Create a persistent cache in the filesystem.

        If the cache does not yet exist, it will be created. The cache will
        never overwrite existing directories.

        All files will be saved and loaded in the given `encoding`.
        Only files which match any file extension defined in `file_ext`
        will be read.
        For saving a file the first value of `file_ext`will be used.
        """
        super(FileCache, self).__init__(cache_dir)
        self._file_ext = file_ext
        self._encoding = encoding
        ensure_directory(self._root)

    def _page_location(self, page):
        """Determine where a page is stored in the file cache.

        If a page is not stored in the filesystem yet, a new location will
        be generated.
        The location consists of the base path of the cache, the name of the
        page (e.g. foo/bar) and the first file extension found in the
        `file_ext`.
        """
        if page.location is None:
            path = page.name

            try:
                location = self._root / (path + self._file_ext[0])
            except UnicodeEncodeError:
                # encode the string in py2
                path = path.encode(self._encoding)
                location = self._root / (path + self._file_ext[0])

            ensure_directory(location.absolute().parent)
            page.location = location
            return location

        else:
            return page.location

    def store_page(self, page):
        """Save the page on the file system.

        The page will be saved with the defined encoding for the cache.
        """
        location = self._page_location(page)
        with location.open(mode='w', encoding=self._encoding) as fp:
            content = page.as_buffer()

            fp.write(compat.text_type(content.getvalue()))
            content.close()

        return True

    def load_page(self, page):
        """Load the page from the file system.

        Each loaded file will be put into an internal dict as :class:`Page`
        and `mtime` tuple.
        The internal dict acts as memory cache. This shall prevent further
        accesses to the filesystem if the modification time of the given page
        has not changed since it was last loaded.
        """
        mtime = page.location.stat().st_mtime
        filename = page.location.absolute()
        cached = self._cache.get(filename)

        if cached and cached[1] == mtime:
            return cached[0]
        else:
            with page.location.open(encoding=self._encoding) as fp:
                content = fp.read()
                page.load_content(content)
            self._cache[filename] = (page, mtime)
            return page

    def load_pages(self, html_renderer):
        """
        Load all pages found in this cache and assign each :class:`Page`
        object the defined `html_renderer`.
        """
        pages = {}
        for extension in self._file_ext:
            pattern = u'**/*%s' % (extension,)
            for path in self._root.glob(pattern):
                rel_path = path.relative_to(self._root)
                name = '/'.join(rel_path.parts)
                name = name[:-len(extension)]
                try:
                    name = name.decode(self._encoding)
                except AttributeError:
                    pass
                name = unicodedata.normalize('NFC', name)

                page = self.load_page(Page(name, path, html_renderer))
                pages[name] = page

        return pages

    def delete_page(self, page):
        """Delete a page from the cache and filesystem."""
        location = page.location
        if location is None:
            return False

        del self._cache[location]
        location.unlink()
        return True


class SQLiteCache(BaseCache):

    """A SQLite cache, which stores :class:`Page` objects a database."""

    def __init__(self, cache_dir, encoding):
        """Create a persistent database in the filesystem.

        If the cache does not yet exist, it will be created at the path
        `cache_db`. The cache will never overwrite existing databases.

        All :class:`Page` object contents will be saved and loaded in the
        given `encoding`.
        """
        super(SQLiteCache, self).__init__(cache_dir)
        self._cache_db = self._root / u'pages.db'
        self._encoding = encoding
        self._db_conn_cache = threading.local()
        self._ensure_db()

    @property
    def db(self):
        """Initalize a connection to the database."""
        if not getattr(self._db_conn_cache, u'db', None):
            self._ensure_db()
            self._db_conn_cache.db = sqlite3.connect(
                compat.text_type(self._cache_db))
        return self._db_conn_cache.db

    def _ensure_db(self):
        """Create the database and all necessary tables."""
        if not self._cache_db.exists():
            ensure_directory(self._root)
            db = sqlite3.connect(compat.text_type(self._cache_db))
            stmt = """
                CREATE TABLE pages (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    content BLOB,
                    last_modified datetime DEFAULT
                        (datetime('now', 'localtime'))
                );
            """
            db.execute(stmt)
            db.commit()
            db.close()

    def cleanup(self):
        """Close all open connection and remove them from cache."""
        if getattr(self._db_conn_cache, u'db', None):
            self._db_conn_cache.db.close()
        self._db_conn_cache.db = None

    def load_page(self, page):
        """Load the page from the database.

        Each loaded page will be put into an internal dict as :class:`Page`
        and `mtime` tuple.
        The internal dict acts as memory cache. This shall prevent further
        parsing of content of the page if the modification time of the
        given page has not changed since it was last loaded.
        """
        stmt = u'SELECT content, last_modified FROM pages WHERE id=?'
        page_id = page.location

        cursor = self.db.cursor()
        try:
            cursor.execute(stmt, (page_id,))
        except sqlite3.OperationalError:
            cursor.close()
            return None

        row = cursor.fetchone()
        mtime = row[1]
        cached = self._cache.get(page_id)

        cursor.close()

        if cached and cached[1] == mtime:
            return cached[0]
        else:
            content = compat.StringIO(row[0])
            page.load_content(content.getvalue())
            self._cache[page_id] = (page, mtime)
            return page

    def load_pages(self, html_renderer):
        """
        Load all pages found in this cache and assign each :class:`Page`
        object the defined `html_renderer`.
        """
        pages = {}

        stmt = u'SELECT id, name FROM pages'
        cursor = self.db.cursor()

        try:
            cursor.execute(stmt)
        except sqlite3.OperationalError:
            return pages

        for row in cursor.fetchall():
            name = row[1]
            page = self.load_page(Page(name, row[0], html_renderer))
            if page:
                pages[name] = page

        return pages

    def store_page(self, page):
        """Save the page in the database.

        Each page will get a new unique ID as primary key in the database.
        All content of a page will be saved as a blob type.
        Furthermore the time of inserting the page will be saved.
        """
        stmt = u"""INSERT INTO pages (name, content, last_modified)
                  VALUES (?, ?, datetime(?, 'unixepoch', 'localtime'))"""

        cursor = self.db.cursor()
        try:
            cursor.execute(stmt, (page.name, page.as_buffer().getvalue(),
                                  time.time()))
        except sqlite3.OperationalError:
            cursor.close()
            return False
        except sqlite3.IntegrityError:
            try:
                stmt = u"""UPDATE pages SET content = ?,
                          last_modified = datetime(?, 'unixepoch', 'localtime')
                          WHERE name = ?"""
                cursor.execute(stmt, (page.as_buffer().getvalue(),
                               time.time(), page.name))
            except sqlite3.OperationalError:
                cursor.close()
                return False

        cursor.close()
        self.db.commit()

        return True

    def delete_page(self, page):
        """Delete the page from the cache and database."""
        stmt = u'DELETE FROM pages WHERE id=?'
        page_id = page.location

        cursor = self.db.cursor()
        try:
            cursor.execute(stmt, (page_id,))
        except sqlite3.OperationalError:
            cursor.close()
            return False

        cursor.close()
        self.db.commit()
        del self._cache[page.location]
        return True

    def __del__(self):
        """Close all open database connections."""
        self.cleanup()
