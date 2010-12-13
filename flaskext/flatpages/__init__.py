from __future__ import with_statement

import os.path
import itertools

import yaml
import markdown
import werkzeug
import flask


class Page(object):
    def __init__(self, path, meta_yaml, source):
        self.path = path
        self._meta_yaml = meta_yaml
        self.source = source
    
    def __repr__(self):
        return '<Page %r>' % self.path

    @werkzeug.cached_property
    def html(self):
        return markdown.markdown(self.source)

    # Used by jinja when directly printing this object in a template.
    # Jinja assumes that the return value is safe and needs to escaping (which
    # is what we want).
    def __html__(self):
        return self.html

    @werkzeug.cached_property
    def meta(self):
        meta = yaml.safe_load(self._meta_yaml)
        # YAML documents can be any type but we want a dict
        # eg. yaml.safe_load('') -> None
        #     yaml.safe_load('- 1\n- a') -> [1, 'a']
        if not meta:
            return {}
        assert isinstance(meta, dict)
        return meta

    def __getitem__(self, name):
        return self.meta[name]
    

class FlatPages(object):    
    def __init__(self, app):
        app.config.setdefault('FLATPAGES_ROOT', 'pages')
        app.config.setdefault('FLATPAGES_EXTENSION', '.html')
        app.config.setdefault('FLATPAGES_ENCODING', 'utf8')
        app.config.setdefault('FLATPAGES_DEFAULT_TEMPLATE', 'flatpage.html')
        self.app = app
        
        #: dict of filename: (page object, mtime when loaded)
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
    
    def render(self, path):
        """Render a template with the page at `path`. Abort with a 404 error on
        non-existent pages. The template name is taken from the page's
        `template` metadata and defaults to `FlatPages.default_template`.
        
        Can be used as follows::

            app.add_url_rule('/<path:path>/', 'flatpage', pages.render)
        
        Warning: such an URL rule should be declared last so that is does not
        shadow more specific rules.
        """
        page = self.get_or_404(path)
        default_template = self.app.config['FLATPAGES_DEFAULT_TEMPLATE']
        template = page.meta.get('template', default_template)
        return flask.render_template(template, page=page)

    def _ensure_loaded(self):
        """Make sure pages are loaded."""
        if self._pages is None:
            self._load_all()
    
    @property
    def root(self):
        """Full path to the directory where pages are looked for.
        
        It is the `FLATPAGES_ROOT` config value, interpreted as relative to
        the app root directory.
        """
        return os.path.join(self.app.root_path,
                            self.app.config['FLATPAGES_ROOT'])

    def _load_all(self):
        """Walk the page root directory an load all pages."""
        def _walk(directory, path_prefix=()):
            for name in os.listdir(directory):
                full_name = os.path.join(directory, name)
                if os.path.isdir(full_name):
                    _walk(full_name, path_prefix + (name,))
                elif name.endswith(extension):
                    name_without_extension = name[:-len(extension)]
                    path = u'/'.join(path_prefix + (name_without_extension,))
                    self._load_file(path, full_name)
        
        self._pages = {}
        extension = self.app.config['FLATPAGES_EXTENSION']
        _walk(self.root)
    
    def _load_file(self, path, filename):
        mtime = os.path.getmtime(filename)
        cached = self._file_cache.get(filename)
        if cached and cached[1] == mtime:
            # cached == (page, old_mtime)
            page = cached[0]
        else:
            with open(filename) as fd:
                content = fd.read().decode(
                    self.app.config['FLATPAGES_ENCODING'])
            page = self._parse(content, path)
            self._file_cache[filename] = page, mtime
        self._pages[path] = page
        return page
    
    def _parse(self, string, path):
        lines = iter(string.split(u'\n'))
        # Read lines until an empty line is encountered.
        meta = u'\n'.join(itertools.takewhile(unicode.strip, lines))
        # The rest is the content. `lines` is an iterator so it continues
        # where `itertools.takewhile` left it.
        content = u'\n'.join(lines)

        return Page(path, meta, content)
    

