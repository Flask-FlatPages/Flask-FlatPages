# coding: utf8

def exact(page, field, value):
    return getattr(page, field) == value

def exists(page, field, value):
    return (getattr(page, field) != None) == value

def contains(page, field, value):
    return value in (getattr(page, field) or [])

def in_(page, field, value):
    return getattr(page, field) in (value or [])

def iexact(page, field, value):
    """Case-insensitive exact()."""
    try:
        res = getattr(page, field).lower() == value.lower()
    except AttributeError:
        return False
    else:
        return res

def icontains(page, field, value):
    """Case-insensitive contains()."""
    try:
        _field = getattr(page, field)
        if isinstance(_field, (str, unicode)):
            res = value.lower() in _field.lower()
        else:
            res = value.lower() in (
                    val.lower() for val in (getattr(page, field) or []))
    except AttributeError:
        return False
    else:
        return res

def startswith(page, field, value):
    _field = getattr(page, field)
    if isinstance(_field, (str, unicode)):
        return _field.startswith(value)
    return False

def istartswith(page, field, value):
    res = False
    try:
        _field = getattr(page, field)
        res = _field.lower().startswith(value.lower())
    except AttributeError:
        pass
    return res
