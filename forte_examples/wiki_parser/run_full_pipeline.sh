EXAMPLEDIR=$(dirname $0)
ROOTDIR=$EXAMPLEDIR/../..

### Step 1: Docker Packaging
python $ROOTDIR/bin/pircli dockerize \
    --auto $ROOTDIR \
	--pipeline forte_examples.wiki_parser.full_pipeline:full_pipeline \
	--output $EXAMPLEDIR/full_pipeline.yml \
	--flatten

# Convert EXAMPLEDIR to absolute path since docker can't bind-mount relative paths.
EXAMPLEDIR=$([[ $EXAMPLEDIR = /* ]] && echo "$EXAMPLEDIR" || echo "$PWD/${EXAMPLEDIR#./}")

### Step 2: Generate Argo YAML
INPUT_input_dir=$EXAMPLEDIR/inputs/dbpedia_full/ \
OUTPUT=$EXAMPLEDIR/outputs \
NFS_SERVER=k8s-master.cm.cluster \
python $ROOTDIR/bin/pircli generate $EXAMPLEDIR/full_pipeline.yml \
	--target pirlib.backends.argo_batch:ArgoBatchBackend \
	--output $EXAMPLEDIR/full-pipeline-argo.yml

### Step 3: Execute the Argo Workflow
argo submit -n argo --watch $EXAMPLEDIR/wiki_parser/full-pipeline-argo.yml


