import pandas
import tempfile
import yaml
from dataclasses import asdict
from typing import Tuple

from pirlib.frameworks.adaptdl import AdaptDL
from pirlib.iotypes import DirectoryPath, FilePath
from pirlib.operator import operator
from pirlib.pipeline import pipeline


@operator
def clean(dataset: DirectoryPath) -> DirectoryPath:
    with open(dataset / "file.txt") as f:
        print("clean({})".format(f.read().strip()))
    outdir = operator.context().output
    with open(outdir / "file.txt", "w") as f:
        f.write("clean_result")
    return outdir


@operator(framework=AdaptDL(min_replicas=1, max_replicas=4))
def train(dataset: DirectoryPath) -> FilePath:
    with open(dataset / "file.txt") as f:
        print("train({})".format(f.read().strip()))
    outfile = operator.context().output
    with open(outfile, "w") as f:
        f.write("train_result")
    return outfile


@operator
def evaluate(test_dataset: DirectoryPath, predictions: DirectoryPath) -> pandas.DataFrame:
    with open(test_dataset / "file.txt") as f, open(predictions / "file.txt") as g:
        print("evaluate({}, {})".format(f.read().strip(), g.read().strip()))
    outdir = operator.context().output
    df = pandas.DataFrame([{"evaluate": "result"}])
    return df


@operator
def translate(model: FilePath, sentences: DirectoryPath) -> DirectoryPath:
    opctx = operator.context()
    with open(model) as f, open(sentences / "file.txt") as g:
        print("translate({}, {}, config={})".format(f.read().strip(), g.read().strip(), opctx.config))
    outdir = opctx.output
    with open(outdir / "file.txt", "w") as f:
        f.write("translate_result")
    return outdir


@operator
def sentiment(model: FilePath, sentences: DirectoryPath) -> DirectoryPath:
    with open(model) as f, open(sentences / "file.txt") as g:
        print("sentiment({}, {})".format(f.read().strip(), g.read().strip()))
    outdir = operator.context().output
    with open(outdir / "file.txt", "w") as f:
        f.write("sentiment_result")
    return outdir


@pipeline
def infer_pipeline(translate_model: FilePath,
                   sentiment_model: FilePath,
                   sentences: DirectoryPath) -> pandas.DataFrame:
    translate_1 = translate.instance("translate_1")
    translate_1.config["key"] = "value"
    return sentiment(sentiment_model, translate_1(translate_model, sentences))


@pipeline
def train_pipeline(
        train_dataset: DirectoryPath,
        translate_model: FilePath,
        sentences: DirectoryPath,
    ) -> Tuple[FilePath, pandas.DataFrame]:
    sentiment_model = train(clean(train_dataset))
    sentiment = infer_pipeline(translate_model, sentiment_model, sentences)
    return sentiment_model, evaluate(sentences, sentiment)


if __name__ == "__main__":
    package = train_pipeline.package()
    print(yaml.dump(asdict(package), sort_keys=False))
    dir_1 = tempfile.TemporaryDirectory()
    file_2 = tempfile.NamedTemporaryFile()
    dir_3 = tempfile.TemporaryDirectory()
    with open(f"{dir_1.name}/file.txt", "w") as f:
        f.write("train_dataset")
    with open(f"{file_2.name}", "w") as f:
        f.write("translate_model")
    with open(f"{dir_3.name}/file.txt", "w") as f:
        f.write("sentences")
    model_path, metrics = train_pipeline(DirectoryPath(dir_1.name),
                                         FilePath(file_2.name),
                                         DirectoryPath(dir_3.name))
    with open(model_path) as f:
        print("pipeline model: {}".format(f.read().strip()))
    print("pipeline metrics: {}".format(metrics.to_records()))
