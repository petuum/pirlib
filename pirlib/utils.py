def find_by_id(iterable, id):
    for item in iterable:
        if item.id == id:
            return item
