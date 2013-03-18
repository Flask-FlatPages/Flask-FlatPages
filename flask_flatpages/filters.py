# coding: utf8

def exact(page, field, value):
    return page.meta.get(field) == value

def isnull(page, field, value):
    return (page.meta.get(field) == None) == value

def contains(page, field, value):
    return value in page.meta.get(field, [])

def iexact(page, field, value):
    """Case-insensitive exact()."""
    try:
        res = page.meta.get(field).lower() == value.lower()
    except AttributeError:
        return False
    else:
        return res

def icontains(page, field, value):
    """Case-insensitive contains()."""
    try:
        res = value.lower() in (val.lower() for val in page.meta.get(field, []))
    except AttributeError:
        return False
    else:
        return res
