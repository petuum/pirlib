EXAMPLEDIR=$(dirname $0)
ROOTDIR=$EXAMPLEDIR/../..

### Step 1: Docker Packaging
python $ROOTDIR/bin/pircli dockerize \
    --auto $ROOTDIR \
	--pipeline forte_examples.wiki_parser.one_step:sample_pipeline \
	--output $EXAMPLEDIR/one_step_sample.yml \
	--flatten

# Convert EXAMPLEDIR to absolute path since docker can't bind-mount relative paths.
EXAMPLEDIR=$([[ $EXAMPLEDIR = /* ]] && echo "$EXAMPLEDIR" || echo "$PWD/${EXAMPLEDIR#./}")

### Step 2: Generate Argo YAML
INPUT_input_dir=$EXAMPLEDIR/inputs/dbpedia/ \
OUTPUT=$EXAMPLEDIR/outputs \
NFS_SERVER=k8s-master.cm.cluster \
python $ROOTDIR/bin/pircli generate $EXAMPLEDIR/one_step_sample.yml \
	--target pirlib.backends.argo_batch:ArgoBatchBackend \
	--output $EXAMPLEDIR/one-step-wiki-parse-argo.yml

### Step 3: Execute the Argo Workflow
argo submit -n argo --watch forte_examples/wiki_parser/one-step-wiki-parse-argo.yml