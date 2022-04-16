def find_by_name(iterable, name):
    for item in iterable:
        if item.name == name:
            return item
