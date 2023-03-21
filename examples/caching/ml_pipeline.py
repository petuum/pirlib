import time

from pirlib.iotypes import DirectoryPath, FilePath
from pirlib.pipeline import pipeline
from pirlib.task import task


@task(cache=True, cache_key_file="hparams")
def preprocess(dataset: DirectoryPath, *, hparams: FilePath) -> DirectoryPath:
    # Read the raw data.
    with (dataset / "data.txt").open("r") as f:
        data = f.read()

    with hparams.open("r") as f:
        hp = f.read()

    output_dir = task.context().output

    # Write the preprocessed data in the output directory.
    with (output_dir / "preprocessed_data.txt").open("w") as f:
        f.write(f"{data}_preprocessed_{hp}")

    # time.sleep is used to imitate processing time
    time.sleep(10)
    return output_dir


@task(cache=True, cache_key_file="hparams")
def train(preprocessed_dir: DirectoryPath, *, hparams: FilePath) -> DirectoryPath:
    # Read the preprocessed data.
    with (preprocessed_dir / "preprocessed_data.txt").open("r") as f:
        data = f.read()

    with hparams.open("r") as f:
        hp = f.read()

    output_dir = task.context().output

    # Write the trained model.
    with (output_dir / "model.txt").open("w") as f:
        f.write(f"model_{hp} trained on [{data}]")

    # time.sleep is used to imitate processing time
    time.sleep(10)
    return output_dir


@task(cache=True, cache_key_file="hparams")
def postprocess(
    preprocessed_dir: DirectoryPath, model_dir: DirectoryPath, *, hparams: FilePath
) -> DirectoryPath:
    # Read the preprocessed data.
    with (preprocessed_dir / "preprocessed_data.txt").open("r") as f:
        data = f.read()

    with hparams.open("r") as f:
        hp = f.read()

    # Load the trained model.
    with (model_dir / "model.txt").open("r") as f:
        model = f.read()

    output_dir = task.context().output

    # Write the posprocessed data.
    with (output_dir / "postprocessed_data.txt").open("w") as f:
        f.write(f"postprocessed_{hp} the [{data}] using [{model}].")

    # time.sleep is used to imitate processing time
    time.sleep(10)
    return output_dir


@pipeline
def ml_job(
    raw_data: DirectoryPath, preproc_hp: FilePath, train_hp: FilePath, postproc_hp: FilePath
) -> DirectoryPath:

    preprocess_data = preprocess(raw_data, hparams=preproc_hp)
    train_model = train(preprocess_data, hparams=train_hp)
    postprocess_data = postprocess(preprocess_data, train_model, hparams=postproc_hp)
    return postprocess_data
