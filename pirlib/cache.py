import shutil
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from diskcache import Cache

CACHE_DIR = "../tmp/cache"


def cache_directory(dir_path: Path, cache_key: str) -> bool:
    """Caches a given directory with the given key.

    :param dir_path: The directory to be cached.
    :type dir_path: Path
    :param cache_key: An key that will be used to retreive the cached directiry.
    :type cache_key: str
    :return: True if caching was a success, False if the key already exists.
    :rtype: bool
    """
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


def fetch_directory(dir_path: Path, cache_key: str) -> bool:
    """Retrieves a cached directory. Contents of the existing directory
    will get overwritten if they share the same file name with that of the
    files in the cache.

    :param dir_path: The directory which needs to be fetched. The directory
    will be created if it doesn't already exist.
    :type dir_path: Path
    :param cache_key: The cache key which uniquely identifies the directory.
    :type cache_key: str
    :return: True if the directory was retrived successfully, False otherwise.
    :rtype: bool
    """
    # Retreive the zip bytestream if key exists.
    with Cache(CACHE_DIR) as cache_ref:
        if cache_key in cache_ref:
            zipped_stream = cache_ref.get(cache_key)
        else:
            return False

    # Create a ZipFile object from the bystream.
    with ZipFile(zipped_stream, mode="r") as zipped_dir:
        # Extract the ziped directory in the provided path.
        zipped_dir.extractall(path=dir_path)

    return True
