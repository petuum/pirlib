EXAMPLEDIR=$(dirname $0)
ROOTDIR=$EXAMPLEDIR/..

PYTHONPATH=$ROOTDIR $ROOTDIR/bin/pircli dockerize --auto $ROOTDIR \
	--pipeline example.example:train_pipeline \
	--output $EXAMPLEDIR/package_docker.yml \
    --flatten

PYTHONPATH=$ROOTDIR $ROOTDIR/bin/pircli generate $EXAMPLEDIR/package_docker.yml \
	--target pirlib.backends.docker_batch:DockerBatchBackend \
	--output $EXAMPLEDIR/docker-compose.yml

# Convert EXAMPLEDIR to absolute path since docker can't bind-mount relative paths.
EXAMPLEDIR=$([[ $EXAMPLEDIR = /* ]] && echo "$EXAMPLEDIR" || echo "$PWD/${EXAMPLEDIR#./}")

INPUT_train_dataset=$EXAMPLEDIR/inputs/train_dataset \
INPUT_translate_model=$EXAMPLEDIR/inputs \
INPUT_sentences=$EXAMPLEDIR/inputs/sentences \
OUTPUT=$EXAMPLEDIR/outputs \
docker-compose -f $EXAMPLEDIR/docker-compose.yml up --force-recreate -V

INPUT_train_dataset=$EXAMPLEDIR/inputs/train_dataset \
INPUT_translate_model=$EXAMPLEDIR/inputs/translate_model.txt \
INPUT_sentences=$EXAMPLEDIR/inputs/sentences \
OUTPUT=$EXAMPLEDIR/outputs \
docker-compose -f $EXAMPLEDIR/docker-compose.yml down -v
