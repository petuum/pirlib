def find_by_name(iterable, name):
    for item in iterable:
        if item.name == name:
            return item

def find_by_id_prefix(iterable, prefix):
    results = []
    for key in iterable:
        if key.startswith(prefix):
            results.append(iterable[key])
    return results