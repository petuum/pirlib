import pandas
import tempfile
import yaml
from dataclasses import asdict
from typing import Tuple, TypedDict

from pirlib.frameworks.adaptdl import AdaptDL
from pirlib.iotypes import DirectoryPath, FilePath
from pirlib.task import task
from pirlib.pipeline import pipeline


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
    task_ctx = task.context()
    with open(dataset / "file.txt") as f:
        print("train({}, config={})".format(f.read().strip(), task_ctx.config))
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
    df = pandas.DataFrame([{"evaluate": "result"}])
    return df


class TranslateModel(object):
    def translate(self, inp: str) -> str:
        output = f"translation: {inp}"
        return output


@task
def translate(sentences: DirectoryPath) -> DirectoryPath:
    task_ctx = task.context()
    model = task_ctx.translate_model
    with open(sentences / "file.txt") as g:
        inp = g.read().strip()
        print(
            "translate({}, config={})".format(
                inp,
                task_ctx.config)
        )
        translate_result = model.translate(inp)
    outdir = task_ctx.output
    with open(outdir / "file.txt", "w") as f:
        f.write(translate_result)
    return outdir


@translate.setup
def translate_setup() -> None:
    task_ctx = task.context()
    task_ctx.translate_model = TranslateModel()
    print(">>> Initialized translation model.")


@translate.teardown
def translate_teardown() -> None:
    task_ctx = task.context()
    del task_ctx.translate_model
    print(">>> Cleaned up translation model.")


@task
def sentiment(model: FilePath, sentences: DirectoryPath) -> DirectoryPath:
    with open(model) as f, open(sentences / "file.txt") as g:
        print("sentiment({}, {})".format(f.read().strip(), g.read().strip()))
    outdir = task.context().output
    with open(outdir / "file.txt", "w") as f:
        f.write("sentiment_result")
    return outdir


@pipeline
def infer_pipeline(sentiment_model: FilePath,
                   sentences: DirectoryPath) -> DirectoryPath:
    translate_1 = translate.instance("translate_1")
    translate_1.config["key"] = "value"
    return sentiment(sentiment_model, translate_1(sentences))


@pipeline
def train_pipeline(
        train_dataset: DirectoryPath,
        sentences: DirectoryPath) -> Tuple[FilePath, pandas.DataFrame]:
    sentiment_model = train(clean(train_dataset))
    sentiment = infer_pipeline(sentiment_model, sentences)
    eval_input = {"test_dataset": sentences, "predictions": sentiment}
    return sentiment_model, evaluate(eval_input)


if __name__ == "__main__":
    package = train_pipeline.package()
    print(yaml.dump(asdict(package), sort_keys=False))
    # Prepare inputs.
    dir_1 = tempfile.TemporaryDirectory()
    dir_3 = tempfile.TemporaryDirectory()
    with open(f"{dir_1.name}/file.txt", "w") as f:
        f.write("train_dataset")
    with open(f"{dir_3.name}/file.txt", "w") as f:
        f.write("sentences")
    # Test calling end-to-end pipeline.
    model_path, metrics = train_pipeline(DirectoryPath(dir_1.name),
                                         DirectoryPath(dir_3.name))
    with open(model_path) as f:
        print("pipeline model: {}".format(f.read().strip()))
    print("pipeline metrics: {}".format(metrics.to_records()))

    # Test calling single operator.
    cleaned_path = clean(DirectoryPath(dir_1.name))
    with open(cleaned_path / "file.txt") as f:
        print("cleaned dataset: {}".format(f.read().strip()))
