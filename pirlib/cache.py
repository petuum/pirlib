import hashlib
import os
import shutil

from diskcache import Cache

from pirlib.iotypes import DirectoryPath, FilePath

CACHE_DIR = os.getenv("PIRLIB_CACHE_DIR", "/pirlib/cache")


def cache_directory(dir_path: DirectoryPath, cache_key: str) -> bool:
    """Caches a given directory with the given key.

    :param dir_path: The directory to be cached.
    :type dir_path: Path
    :param cache_key: An key that will be used to retreive the cached directiry.
    :type cache_key: str
    :return: True if caching was a success, False if the key already exists.
    :rtype: bool
    """
    with Cache(CACHE_DIR) as cache_ref:
        if cache_key in cache_ref:
            # Key already exists, caching not possible.
            return False
        else:
            # Key doesn't exist, caching is possible.
            # Copy the contents to a directory in the cache.
            target_dir = os.path.join(CACHE_DIR, f"DIR_{cache_key}")
            shutil.copytree(dir_path, target_dir)
            # Add the temp directory to the cache.
            status = cache_ref.add(cache_key, target_dir)

    # Return the status of cache add operation.
    return status


def fetch_directory(dir_path: DirectoryPath, cache_key: str) -> bool:
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
    # Retreive the temp directory location if key exists.
    with Cache(CACHE_DIR) as cache_ref:
        if cache_key in cache_ref:
            cached_dir = cache_ref.get(cache_key)
        else:
            return False

    # Copy the contents of the temp directory to the given directory.
    shutil.copytree(cached_dir, dir_path, dirs_exist_ok=True)

    return True


def generate_cache_key(key_file: FilePath) -> str:
    """Create cache key given an input file.

    :param key_file: Input file to read the key.
    :type key_file: Path
    :return: hashed value of the key read.
    :rtype: str
    """

    # Read contents of key file as a string.
    with open(str(key_file), "r") as f:
        key_data = f.read()

    # Compute a hash value from the key file contents.
    cache_key = hashlib.sha256(f"{str(key_file)}_{key_data}".encode()).hexdigest()
    return cache_key
