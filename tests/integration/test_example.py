import pandas
import tempfile
import yaml
from dataclasses import asdict
from typing import Tuple, TypedDict

from pirlib.frameworks.adaptdl import AdaptDL
from pirlib.iotypes import DirectoryPath, FilePath
from pirlib.task import task
from pirlib.pipeline import pipeline

from pirlib.pir import Graph


@task
def clean(dataset: DirectoryPath) -> DirectoryPath:
    with open(dataset / "file.txt") as f:
        print("clean({})".format(f.read().strip()))
    outdir = task.context().output
    with open(outdir / "file.txt", "w") as f:
        f.write("clean_result")
    return outdir


@task(framework=AdaptDL(min_replicas=1, max_replicas=4))
def train(dataset: DirectoryPath) -> FilePath:
    with open(dataset / "file.txt") as f:
        print("train({})".format(f.read().strip()))
    outfile = task.context().output
    with open(outfile, "w") as f:
        f.write("train_result")
    return outfile


class EvaluateInput(TypedDict):
    test_dataset: DirectoryPath
    predictions: DirectoryPath


@task
def evaluate(kwargs: EvaluateInput) -> pandas.DataFrame:
    test_dataset = kwargs["test_dataset"]
    predictions = kwargs["predictions"]
    with open(test_dataset / "file.txt") as f, open(predictions / "file.txt") as g:
        print("evaluate({}, {})".format(f.read().strip(), g.read().strip()))
    outdir = task.context().output
    df = pandas.DataFrame([{"evaluate": "result"}])
    return df


@task
def translate(args: Tuple[FilePath, DirectoryPath]) -> DirectoryPath:
    model, sentences = args
    opctx = task.context()
    with open(model) as f, open(sentences / "file.txt") as g:
        print("translate({}, {}, config={})".format(f.read().strip(), g.read().strip(), opctx.config))
    outdir = opctx.output
    with open(outdir / "file.txt", "w") as f:
        f.write("translate_result")
    return outdir


@task
def sentiment(model: FilePath, sentences: DirectoryPath) -> DirectoryPath:
    with open(model) as f, open(sentences / "file.txt") as g:
        print("sentiment({}, {})".format(f.read().strip(), g.read().strip()))
    outdir = task.context().output
    with open(outdir / "file.txt", "w") as f:
        f.write("sentiment_result")
    return outdir


@pipeline
def infer_pipeline(translate_model: FilePath,
                   sentiment_model: FilePath,
                   sentences: DirectoryPath) -> DirectoryPath:
    translate_1 = translate.instance("translate_1")
    translate_1.config["key"] = "value"
    return sentiment(sentiment_model, translate_1((translate_model, sentences)))


@pipeline
def train_pipeline(
        train_dataset: DirectoryPath,
        translate_model: FilePath,
        sentences: DirectoryPath,
    ) -> Tuple[FilePath, pandas.DataFrame]:
    sentiment_model = train(clean(train_dataset))
    sentiment = infer_pipeline(translate_model, sentiment_model, sentences)
    eval_input = {"test_dataset": sentences, "predictions": sentiment}
    return sentiment_model, evaluate(eval_input)



def test_pipeline_run():
    # Prepare inputs.
    dir_1 = tempfile.TemporaryDirectory()
    file_2 = tempfile.NamedTemporaryFile()
    dir_3 = tempfile.TemporaryDirectory()
    with open(f"{dir_1.name}/file.txt", "w") as f:
        f.write("train_dataset")
    with open(f"{file_2.name}", "w") as f:
        f.write("translate_model")
    with open(f"{dir_3.name}/file.txt", "w") as f:
        f.write("sentences")
    # Test calling end-to-end pipeline.
    model_path, metrics = train_pipeline(DirectoryPath(dir_1.name),
                                         FilePath(file_2.name),
                                         DirectoryPath(dir_3.name))
    with open(model_path) as f:
        assert f.read().strip() == "train_result"
    record = metrics.to_records()[0]
    assert record[0] == 0, record[1] == "result"


def test_task_run():
    # Prepare inputs.
    dir_1 = tempfile.TemporaryDirectory()
    with open(f"{dir_1.name}/file.txt", "w") as f:
        f.write("train_dataset")
    ## Test calling single operator.
    cleaned_path = clean(DirectoryPath(dir_1.name))
    with open(cleaned_path / "file.txt") as f:
        assert  f.read().strip() == "clean_result"
