import pathlib

from dataclasses import dataclass

_TYPE_MAP = {
    int: "INT",
    float: "FLOAT",
    str: "STRING",
}


def register_iotype(pytype: type, iotype: str):
    if pytype in _TYPE_MAP and _TYPE_MAP[pytype] != iotype:
        raise ValueError(
            f"{pytype} is already registered " f"as iotype '{_TYPE_MAP[pytype]}'"
        )
    _TYPE_MAP[pytype] = iotype


def pytype_to_iotype(pytype: type):
    if pytype not in _TYPE_MAP:
        raise ValueError(f"{pytype} has not been registered")
    return _TYPE_MAP[pytype]


class DirectoryPath(type(pathlib.Path())):
    pass


class FilePath(type(pathlib.Path())):
    pass


register_iotype(DirectoryPath, "DIRECTORY")
register_iotype(FilePath, "FILE")
try:
    import pandas

    register_iotype(pandas.DataFrame, "DATAFRAME")
except ImportError:
    pass
