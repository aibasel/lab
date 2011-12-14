#! /usr/bin/env python
# -*- coding: utf-8 -*-

import operator
import logging


def uniq(seq):
    """List of unique elements contained in this vector, in order
    of first experience."""
    result = []
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_tuple(atuple):
    if len(atuple) == 1:
        return atuple[0]
    else:
        return atuple


class MissingType(object):
    def __repr__(self):
        return "missing"

missing = MissingType()


def not_missing(val):
    return val is not missing


class ascending(object):
    def __init__(self, value):
        self.wrapped_value = value

class descending(object):
    def __init__(self, value):
        self.wrapped_value = value


class Bunch(dict):
    def key(self, *attrs, **kwargs):
        """A variant of dict.get that looks up several keys at the
        same time and returns a tuple. Default values can be specified
        with the keyword-only argument 'default', which defaults to the
        special object 'missing'."""
        default = kwargs.pop("default", missing)
        assert not kwargs
        return tuple(self.get(attr, default) for attr in attrs)

    def format_attrs(self, *extra_pieces):
        pairs = sorted(self.iteritems())
        pieces = ["%s=%r" % pair for pair in pairs]
        pieces.extend(extra_pieces)
        return ", ".join(pieces)

    def tag(self):
        return "[%s]" % self.format_attrs()

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.format_attrs())


class DataItem(Bunch):
    pass


class DataSet(Bunch):
    def __init__(self, _items=[], **kwargs):
        Bunch.__init__(self, **kwargs)
        if isinstance(_items, DataSet):
            _items = _items.items
        self.items = list(_items)

    def __getitem__(self, key):
        """Look up the key in the data set. If it is not present, look
        it up in all items and return a vector."""
        if key in self:
            return [Bunch.__getitem__(self, key)]
        else:
            return [item.get(key, missing) for item in self.items]

    def get(self, key, default=missing):
        if key in self:
            return [Bunch.__getitem__(self, key)]
        else:
            return [item.get(key, default) for item in self.items]

    def get_single_value(self, key, default=missing):
        """
        Convenience method for a dataset with only one entry
        """
        if key in self:
            return Bunch.__getitem__(self, key)
        else:
            values = [item.get(key, default) for item in self.items]
            assert len(values) <= 1, 'More than one value found for %s in %s' % \
                                        (key, self)
            if len(values) == 0:
                logging.warning('No value found for %s in %s' % (key, self))
                return default
            return values[0]

    def keys(self, *attrs, **kwargs):
        default = kwargs.pop("default", None)
        assert not kwargs
        return [item.key(*attrs, default=default) for item in self.items]

    def __repr__(self):
        attr_text = self.format_attrs("%d items" % len(self.items))
        return "<%s: %s>" % (self.__class__.__name__, attr_text)

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def dump(self, indent=""):
        print indent + str(self)
        for item in self.items:
            print indent + "    " + str(item)

    def append(self, _item=None, **kwargs):
        if _item is None:
            _item = DataItem(**kwargs)
        else:
            assert not kwargs
        self.items.append(_item)

    def filtered(self, *predicates, **pairs):
        copy = DataSet(self)
        copy.filter(*predicates, **pairs)
        return copy

    def filter(self, *predicates, **pairs):
        predicates = list(predicates)
        for key, val in pairs.iteritems():
            predicates.append(lambda item, k=key, v=val: item[k] == v)
        new_items = []
        for item in self.items:
            if all(predicate(item) for predicate in predicates):
                new_items.append(item)
        self.items = new_items

    def sort(self, *keys):
        for key in reversed(keys):
            reverse = False
            if isinstance(key, descending):
                key = key.wrapped_value
                reverse = True
            elif isinstance(key, ascending):
                key = key.wrapped_value
            self.items.sort(key=operator.itemgetter(key), reverse=reverse)

    def group_dict(self, *attrs):
        keys = uniq(self.keys(*attrs))
        result = {}
        for key in keys:
            group_attrs = self.copy()
            group_attrs.update(zip(attrs, key))
            group = DataSet(**group_attrs)
            result[normalize_tuple(key)] = group
        for item in self.items:
            result[normalize_tuple(item.key(*attrs))].append(item)
        return result

    def groups(self, *attrs):
        group_dict = self.group_dict(*attrs)
        keys = map(normalize_tuple, uniq(self.keys(*attrs)))
        return [(key, group_dict[key]) for key in keys]

    def paginate(self, size, *attrs):
        keys = uniq(self.keys(*attrs))
        num_pages = (len(keys) + size - 1) // size
        pages = [DataSet(**self) for _ in xrange(num_pages)]
        key_to_page = dict((key, pages[index // size])
                           for index, key in enumerate(keys))
        for item in self.items:
            key_to_page[item.key(*attrs)].append(item)
        return pages

    def get_attributes(self):
        """
        """
        attrs = set([])
        for item in self.items:
            attrs |= set(item.keys())
        return sorted(list(attrs))

    def copy(self):
        """
        """
        return DataSet(self)



def testme():
    dataset = DataSet(x=1)
    dataset.append(y=2, z=1)
    dataset.append(y=1, z=2)
    dataset.append(y=2, z=1, foo="yes")
    dataset.append(y=3, z="cheesecake")
    dataset.append(y=1, z=None)
    dataset.append(y=0, z=2)

    print "data set:"
    dataset.dump()
    print

    print "grouped by z:"
    for _, group in dataset.groups("z"):
        group.dump(indent="")
    print

    print "grouped by y and z:"
    for _, group in dataset.groups("y", "z"):
        group.dump(indent="")
    print

    print "filtered on z is int:"
    for item in dataset.filtered(lambda item: isinstance(item["z"], int)):
        print item
    print

    print "copy sorted on z descending, then y:"
    copied_dataset = DataSet(dataset)
    copied_dataset.sort(descending("z"), "y")
    copied_dataset.dump()
    print

    print "filter copy on y=2, z=1:"
    copied_dataset.filter(y=2, z=1)
    for item in copied_dataset:
        print item
    print

    print "original dataset:"
    dataset.dump()
    print

    print "paginated on y with page size 2:"
    for page in dataset.paginate(2, "y"):
        page.dump()
    print

    print "x", dataset["x"]
    print "y", dataset["y"]
    print "z", dataset["z"]
    print "foo", dataset["foo"]


if __name__ == "__main__":
    testme()
