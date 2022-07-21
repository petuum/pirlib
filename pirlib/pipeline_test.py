import pytest
from pirlib.pipeline import pipeline
from pirlib.task import task
from pirlib.iotypes import DirectoryPath, FilePath
from pirlib.pir import Graph
from pirlib.utils import find_by_id


pipeline_config = {"key": "value"}
@pipeline(config=pipeline_config)
def p0(inp: FilePath) -> FilePath:
    return inp

@task
def t1(inp: DirectoryPath) -> DirectoryPath:
    return inp

@task
def t2(inp: DirectoryPath) -> FilePath:
    return FilePath(inp / "file.txt")

@pipeline
def p1(inp: DirectoryPath) -> DirectoryPath:
    return t1(inp)

@pipeline
def p2(inp: DirectoryPath) -> FilePath:
    return t2(t1(inp))

@pipeline
def p3(inp: DirectoryPath) -> FilePath:
    return t2(p1(inp))

@pipeline
def broken_pipeline(inp: DirectoryPath) -> FilePath:
    # Output type doesn't match the annotation.
    return t1(inp)


test_dir_path = DirectoryPath("test")
test_file_path = FilePath("test/file.txt")

def test_pipeline_defn():
    assert p0.name == "p0"
    assert p0.config.get("key", None) == "value"


def test_pipeline_pkg():
    pkg_p1 = p1.package()
    pkg_p2 = p2.package()

    assert p1.name == "p1"
    assert p2.name == "p2"
    assert p1.config is None
    assert p2.config is None
    assert len(pkg_p1.graphs) == 1
    assert len(pkg_p2.graphs) == 1
    graph_p1: Graph = pkg_p1.graphs[0]
    graph_p2: Graph = pkg_p2.graphs[0]
    assert len(graph_p1.nodes) == 1
    assert len(graph_p2.nodes) == 2


def test_subgraph_pkg():
    pkg = p3.package()

    assert p3.name == "p3"
    assert p3.config is None
    assert len(pkg.graphs) == 2
    p3_graph = find_by_id(pkg.graphs, "p3")
    assert len(p3_graph.nodes) == 1
    assert len(p3_graph.subgraphs) == 1


def test_run_pipeline():
    assert p1(test_dir_path) == test_dir_path
    assert p2(test_dir_path) == test_file_path
    assert p3(test_dir_path) == test_file_path


def test_wrong_input_type():
    with pytest.raises(TypeError):
        p1(test_file_path)

    with pytest.raises(TypeError):
        p2(test_file_path)

    with pytest.raises(TypeError):
        p3(test_file_path)


def test_wrong_output_type():
    with pytest.raises(TypeError):
        broken_pipeline(test_dir_path)