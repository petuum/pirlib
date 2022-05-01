import urllib.parse
from dataclasses import dataclass
from typing import Optional


@dataclass(init=False)
class IOSpec:
    name: str
    url: urllib.parse.ParseResult
    fmt: Optional[str] = None

    def __init__(self, spec_str: str):
        try:
            name_fmt, url = spec_str.split("=", 1)
            self.url = urllib.parse.urlparse(url)
        except ValueError as err:
            raise ValueError(
                f"could not parse '{spec_str}', expected: " f"'<name>[:<format>]=<url>'"
            ) from None
        name, *fmt = name_fmt.rsplit(":", 1)
        self.name = name
        self.fmt = fmt[0] if fmt else None
