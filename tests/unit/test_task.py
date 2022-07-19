from pirlib.task import task
from pirlib.frameworks.adaptdl import AdaptDL
from pirlib.iotypes import DirectoryPath, FilePath


def test_task_defn1():
    @task
    def my_task(inp: DirectoryPath) -> FilePath:
        return inp / "file.txt"

    assert my_task.name == "my_task"
    assert my_task.config["framework"] is None
    

def test_task_defn2():
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
    def my_task(inp: FilePath) -> FilePath:
        return inp

    assert my_task.name == "my_task"
    assert my_task.config["key"] == "value"
    assert my_task.framework["name"] == "adaptdl"
    assert my_task.framework["version"] == "0.0.0"
    assert my_task.framework["config"]["min_replicas"] == 1
    assert my_task.framework["config"]["max_replicas"] == 4
