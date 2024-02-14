import os
import shutil

import pytest
from flask import Flask

from flask_flatpages import FlatPages


PAGES_DIR = os.path.join(os.path.dirname(__file__), "pages")


@pytest.fixture
def flask_app():
    app = Flask(__name__)
    return app


@pytest.fixture
def app_with_context(flask_app):
    with flask_app.app_context():
        yield flask_app


def _fp_init(app=None, name=None):
    return FlatPages(app, name)


@pytest.fixture
def flatpages_factory():
    return _fp_init


@pytest.fixture
def temp_pages(tmpdir):
    def _temp_fp_init(app: Flask, name: str | None = None) -> FlatPages:
        shutil.copytree(PAGES_DIR, tmpdir, dirs_exist_ok=True)
        fp = _fp_init(app, name)
        if name is None:
            root = "FLATPAGES_ROOT"
        else:
            root = f"FLATPAGES_{name.upper()}_ROOT"
        app.config[root] = tmpdir
        return fp

    yield _temp_fp_init
