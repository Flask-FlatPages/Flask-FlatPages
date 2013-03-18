# coding: utf8

def exact (page, field, value):
    return page.meta.get(field) == value

def isnull(page, field, value):
    return (page.meta.get(field) == None) == value
