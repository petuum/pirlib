import time

from pirlib.iotypes import DirectoryPath, FilePath
from pirlib.pipeline import pipeline
from pirlib.task import task

# def generate_preprocess_key():
#     # Create the parameters for the preprocessing routine.
#     hparams = [1, 2, 3, 4.2, 5]
#     sampled_hparams = random.choice(hparams)
#     # Compute a hash value from the parameters to be used by task wrapper.
#     preprocess_cache_key = hashlib.sha256(f"preprocess_{sampled_hparams}".encode()).hexdigest()
#     return preprocess_cache_key


@task(config=dict(cache=True, cache_key_file="hparams"))
def preprocess(dataset: DirectoryPath, hparams: FilePath) -> DirectoryPath:
    # Read the raw data.
    with (dataset / "data.txt").open("r") as f:
        data = f.read()

    with hparams.open("r") as f:
        hp = f.read()

    output_dir = task.context().output

    # Write the preprocessed data in the output directory.
    with (output_dir / "preprocessed_data.txt").open("w") as f:
        f.write(f"{data}_preprocessed_{hp}")
    time.sleep(3)
    return output_dir


# def generate_train_key():
#     # Create the parameters for the train routine.
#     hparams = [199, 2.12, 12313, 4.2, 123, 5]
#     sampled_hparams = random.choice(hparams)

#     # Compute a hash value from the parameters to be used by task wrapper.
#     train_cache_key = hashlib.sha256(f"train_{sampled_hparams}".encode()).hexdigest()
#     return train_cache_key


@task(config=dict(cache=True, cache_key_file="hparams"))
def train(preprocessed_dir: DirectoryPath, hparams: FilePath) -> DirectoryPath:
    # Read the preprocessed data.
    with (preprocessed_dir / "preprocessed_data.txt").open("r") as f:
        data = f.read()

    with hparams.open("r") as f:
        hp = f.read()

    output_dir = task.context().output

    # Write the trained model.
    with (output_dir / "model.txt").open("w") as f:
        f.write(f"model_{hp} trained on [{data}]")
    time.sleep(3)
    return output_dir


# def generate_key():
#     # Create the parameters for the postprocess routine.
#     hparams = [13, 0.2, 123, 123, 14]
#     sampled_hparams = random.choice(hparams)

#     # Compute a hash value from the parameters to be used by task wrapper.
#     postprocess_cache_key = hashlib.sha256(f"postprocess_{sampled_hparams}".encode()).hexdigest()
#     return postprocess_cache_key


@task(config=dict(cache=True, cache_key_file="hparams"))
def postprocess(
    preprocessed_dir: DirectoryPath, model_dir: DirectoryPath, hparams: FilePath
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
    time.sleep(3)
    return output_dir


@pipeline
def ml_job(
    raw_data: DirectoryPath, preproc_hp: FilePath, train_hp: FilePath, postproc_hp: FilePath
) -> DirectoryPath:

    preprocess_data = preprocess(raw_data, preproc_hp)
    train_model = train(preprocess_data, train_hp)
    postprocess_data = postprocess(preprocess_data, train_model, postproc_hp)
    return postprocess_data
