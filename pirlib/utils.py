def find_by_name(iterable, name):
    ret = []
    for item in iterable:
        if item.name == name:
            ret.append(item)
    return ret

def find_by_id(iterable, id):
    for item in iterable:
        if item.id == id:
            return item

def find_by_id_prefix(iterable, prefix):
    results = []
    for key in iterable:
        if key.startswith(prefix):
            results.append(iterable[key])
    return results