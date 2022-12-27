EXAMPLEDIR=$(dirname $0)
ROOTDIR=$EXAMPLEDIR/../..

### Step 1: Docker Packaging
python $ROOTDIR/bin/pircli dockerize \
    --auto $ROOTDIR \
	--pipeline examples.wiki_parser.sample_pipeline:sample_pipeline \
	--output $EXAMPLEDIR/sample_pipeline.yml \
	--flatten

# Convert EXAMPLEDIR to absolute path since docker can't bind-mount relative paths.
EXAMPLEDIR=$([[ $EXAMPLEDIR = /* ]] && echo "$EXAMPLEDIR" || echo "$PWD/${EXAMPLEDIR#./}")

### Step 2: Generate Argo YAML
INPUT_input_dir=$EXAMPLEDIR/inputs/dbpedia_sample/ \
OUTPUT=$EXAMPLEDIR/outputs \
NFS_SERVER=k8s-master.cm.cluster \
python $ROOTDIR/bin/pircli generate $EXAMPLEDIR/sample_pipeline.yml \
	--target pirlib.backends.argo_batch:ArgoBatchBackend \
	--output $EXAMPLEDIR/sample-pipeline-argo.yml

### Step 3: Execute the Argo Workflow
argo submit -n argo --watch $EXAMPLEDIR/wiki_parser/sample-pipeline-argo.yml


