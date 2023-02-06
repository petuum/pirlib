#%%
import os
import shutil
from io import BytesIO
from pathlib import Path

from diskcache import Cache

CACHE_DIR = "./tmp/cache"
#%%


def cache_directory(dir_path: Path, cache_key: str) -> bool:
    # Zip the contents of the directory.
    zipped_dir = shutil.make_archive(str(dir_path.parts[-1]), "zip", dir_path)

    # Cache the zip file.
    with Cache(CACHE_DIR) as cache_ref:
        # Read the zip file as bytestream.
        with open(zipped_dir, "rb") as f:
            dir_bytes = BytesIO(f.read())

        # Add the zipped stream to the cache.
        status = cache_ref.add(cache_key, dir_bytes)

    # Delete the zipped file.
    Path(zipped_dir).unlink()

    # Return the status of cache add operation.
    return status


#%%
