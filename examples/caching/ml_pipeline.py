import random
import hashlib

from pirlib.iotypes import DirectoryPath, FilePath
from pirlib.pipeline import pipeline
from pirlib.task import task


@task(enable_cache=True, cache_key_var="preprocess_cache_key")
def preprocess(dataset: DirectoryPath) -> DirectoryPath:
    # Read the raw data.
    with (dataset / "data.txt").open("r") as f:
        data = f.read()

    def generate_key():
        # Create the parameters for the preprocessing routine.
        hparams = [1, 2, 3, 4.2, 5]
        preprocess.sampled_hparams = random.choice(hparams)

        # Compute a hash value from the parameters to be used by task wrapper.
        preprocess_cache_key = hashlib.sha256(f"preprocess_{preprocess.sampled_hparams}".encode()).hexdigest()
        return preprocess_cache_key

    output_dir = task.context().output

    # Write the preprocessed data in the output directory.
    with (output_dir / "preprocessed_data.txt").open("w") as f:
        f.write(data + " preprocessed")

    return output_dir

@task(enable_cache=True, cache_key_var="train_cache_key")
def train(preprocessed_dir: DirectoryPath) -> DirectoryPath:
    # Read the preprocessed data.
    with (preprocessed_dir / "preprocessed_data.txt").open("r") as f:
        data = f.read()

    def generate_key():
        # Create the parameters for the train routine.
        hparams = [199, 2.12, 12313, 4.2, 123, 5]
        train.sampled_hparams = random.choice(hparams)

        # Compute a hash value from the parameters to be used by task wrapper.
        train_cache_key = hashlib.sha256(f"train_{train.sampled_hparams}".encode()).hexdigest()
        return train_cache_key

    output_dir = task.context().output

    # Write the trained model.
    with (output_dir / "model.txt").open("w") as f:
        f.write(f"model trained on [{data}]")

    return output_dir


@task(enable_cache=True, cache_key_var="postprocess_cache_key")
def postprocess(
    preprocessed_dir: DirectoryPath, model_dir: DirectoryPath
) -> DirectoryPath:
    # Read the preprocessed data.
    with (preprocessed_dir / "preprocessed_data.txt").open("r") as f:
        data = f.read()

    # Load the trained model.
    with (model_dir / "model.txt").open("r") as f:
        model = f.read()

    def generate_key():
        # Create the parameters for the postprocess routine.
        hparams = [13, 0.2, 123, 123, 14]
        postprocesssampled_hparams = random.choice(hparams)

        # Compute a hash value from the parameters to be used by task wrapper.
        postprocess_cache_key = hashlib.sha256(f"postprocess_{postprocess.sampled_hparams}".encode()).hexdigest()
        return postprocess_cache_key

    output_dir = task.context().output

    # Write the posprocessed data.
    with (output_dir / "postprocessed_data.txt").open("w") as f:
        f.write(f"Postprocessed the [{data}] using [{model}].")

    return output_dir


@pipeline
def ml_job(
    raw_data: DirectoryPath
) -> DirectoryPath:

    preprocess_data = preprocess(raw_data)
    train_model = train(preprocess_data)
    postprocess_data = postprocess(preprocess_data, train_model)
    return postprocess_data