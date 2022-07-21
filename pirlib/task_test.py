import pytest
from pirlib.task import task
from pirlib.frameworks.adaptdl import AdaptDL
from pirlib.iotypes import DirectoryPath, FilePath

@task
def dummy_task(inp: DirectoryPath) -> DirectoryPath:
    return inp

task_config = {"key": "value"}
task_framework = AdaptDL(
    min_replicas=1,
    max_replicas=4,
    version="0.0.0"
)
@task(
    config=task_config,
    framework=task_framework
)
def adaptdl_task(inp: FilePath) -> FilePath:
    return inp

@task
def broken_task(inp: FilePath) -> DirectoryPath:
    # Output type doesn't match the annotation.
    return inp

test_dir_path = DirectoryPath("test")
test_file_path = FilePath("test/file.txt")


def test_task_defn():

    # dummy_task definition
    assert dummy_task.name == "dummy_task"
    assert dummy_task.framework is None
    
    # adaptdl_task definition
    assert adaptdl_task.name == "adaptdl_task"
    assert adaptdl_task.config["key"] == "value"
    assert adaptdl_task.framework.name == "adaptdl"
    assert adaptdl_task.framework.version == "0.0.0"
    assert adaptdl_task.config.get("adaptdl/min_replicas", None) == 1
    assert adaptdl_task.config.get("adaptdl/max_replicas", None) == 4


def test_run_task():
    assert dummy_task(test_dir_path) == test_dir_path
    assert adaptdl_task(test_file_path) == test_file_path


def test_wrong_input_type():
    with pytest.raises(TypeError):
        dummy_task(test_file_path)

    with pytest.raises(TypeError):
        adaptdl_task(test_dir_path)


def test_wrong_output_type():
    with pytest.raises(TypeError):
        broken_task(test_file_path)