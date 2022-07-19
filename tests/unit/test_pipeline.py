from pirlib.pipeline import pipeline
from pirlib.task import task
from pirlib.iotypes import DirectoryPath, FilePath
from pirlib.pir import Graph
from pirlib.utils import find_by_id

def test_pipeline_defn():

    pipeline_config = {"key": "value"}
    @pipeline(config=pipeline_config)
    def my_pipeline(out_path: FilePath) -> FilePath:
        return out_path

    assert my_pipeline.name == "my_pipeline"
    assert my_pipeline.config.get("key", None) == "value"

def test_pipeline_pkg1():
    @task
    def t1(out_path: DirectoryPath) -> DirectoryPath:
        return out_path

    @task
    def t2(int_path: DirectoryPath) -> FilePath:
        return int_path / "file.txt"

    @pipeline
    def p1(out_path: DirectoryPath) -> FilePath:
        return t2(t1(out_path))

    pkg = p1.package()

    assert p1.name == "p1"
    assert p1.config is None
    assert len(pkg.graphs) == 1
    graph: Graph = pkg.graphs[0]
    assert len(graph.nodes) == 2

def test_pipeline_pkg2():
    @task
    def t1(out_path: DirectoryPath) -> DirectoryPath:
        return out_path

    @task
    def t2(int_path: DirectoryPath) -> FilePath:
        return int_path / "file.txt"

    @pipeline
    def p1(int_path: DirectoryPath) -> DirectoryPath:
        return t1(int_path)

    @pipeline
    def p2(out_path: DirectoryPath) -> FilePath:
        return t2(p1(out_path))

    pkg = p2.package()

    assert p2.name == "p2"
    assert p2.config is None
    assert len(pkg.graphs) == 2
    p2_graph = find_by_id(pkg.graphs, "p2")
    assert len(p2_graph.nodes) == 1
    assert len(p2_graph.subgraphs) == 1
