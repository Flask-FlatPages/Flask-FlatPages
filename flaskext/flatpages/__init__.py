from __future__ import with_statement

import os.path
import itertools

import yaml
import markdown
import werkzeug
import flask


class Page(object):
    def __init__(self, path, meta, source):
        self.path = path
        self.meta = meta
        self.source = source

    @werkzeug.cached_property
    def html(self):
        return markdown.markdown(self.source)

    # Used by jinja when directly printing this object in a template.
    # Jinja assumes that the return value is safe and needs to escaping (which
    # is what we want).
    def __html__(self):
        return self.html

    def __getitem__(self, name):
        return self.meta[name]
    

class FlatPages(object):
    
    #: Relative to the app root
    ROOT = 'pages'

    EXTENSION = '.html'
    
    ENCODING = 'utf8'

    def __init__(self, app):
        self.app = app
        self._file_cache = {}
        #: When loaded, a dict of unicode path: page object
        self._pages = None
    
    def reset(self):
        """Forget all pages.
        All pages will be reloaded next time they're accessed"""
        self._pages = None
    
    def __iter__(self):
        """Iterate on all `Page` objects."""
        self._ensure_loaded()
        return self._pages.itervalues()
    
    def get(self, path, default=None):
        """Return the `Page` object at `path` or `default` if there is none."""
        self._ensure_loaded()
        try:
            return self._pages[path]
        except KeyError:
            return default
    
    def get_or_404(self, path):
        """Return the `Page` object at `path` or abort the request
        with a 404 error."""
        page = self.get(path)
        if not page:
            flask.abort(404)
        return page

    def _ensure_loaded(self):
        """Make sure pages are loaded."""
        if self._pages is None:
            self._load_all()

    def _load_all(self):
        """Walk the page root directory an load all pages."""
        self._pages = {}
        def _walk(directory, path_prefix=()):
            for name in os.listdir(directory):
                full_name = os.path.join(directory, name)
                if os.path.isdir(full_name):
                    _walk(full_name, path_prefix + (name,))
                elif name.endswith(self.EXTENSION):
                    name_without_extension = name[:-len(self.EXTENSION)]
                    path = u'/'.join(path_prefix + (name_without_extension,))
                    self._load_file(path, full_name)
        _walk(os.path.join(self.app.root_path, self.ROOT))
    
    def _load_file(self, path, filename):
        mtime = os.path.getmtime(filename)
        cached = self._file_cache.get(filename)
        if cached and cached[1] == mtime:
            # cached == (page, old_mtime)
            page = cached[0]
        else:
            with open(filename) as fd:
                content = fd.read().decode(self.ENCODING)
            page = self._parse(content, path)
            self._file_cache[filename] = page, mtime
        self._pages[path] = page
        return page
    
    def _parse(self, string, path):
        lines = iter(string.split(u'\n'))
        # Read lines until an empty line is encountered.
        meta = u'\n'.join(itertools.takewhile(unicode.strip, lines))
        meta = yaml.safe_load(meta)
        # YAML documents can be any type but we want a dict
        # eg. yaml.safe_load('') -> None
        #     yaml.safe_load('- 1\n- a') -> [1, 'a']
        if not meta:
            meta = {}
        else:
            assert isinstance(meta, dict)
        # The rest is the content. `lines` is an iterator so it continues
        # where `itertools.takewhile` left it.
        content = u'\n'.join(lines)

        return Page(path, meta, content)
    

