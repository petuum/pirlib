EXAMPLEDIR=$(dirname $0)
ROOTDIR=$EXAMPLEDIR/../..

### Module 1: Docker_Packaging
python $ROOTDIR/bin/pircli dockerize \
    $ROOTDIR \
	--auto \
    --pipeline examples.caching.ml_pipeline:ml_job \
	--output $EXAMPLEDIR/package_argo.yml \
	--flatten

# Convert EXAMPLEDIR to absolute path since docker can't bind-mount relative paths.
EXAMPLEDIR=$([[ $EXAMPLEDIR = /* ]] && echo "$EXAMPLEDIR" || echo "$PWD/${EXAMPLEDIR#./}")

### Module 2: Argoize_Module
INPUT_raw_data=$EXAMPLEDIR/dataset \
OUTPUT=$EXAMPLEDIR/outputs \
NFS_SERVER=k8s-master.cm.cluster \
python  $ROOTDIR/bin/pircli generate $EXAMPLEDIR/package_argo.yml \
	--target pirlib.backends.argo_batch:ArgoBatchBackend \
	--output $EXAMPLEDIR/argo-ml-pipeline.yml

# Run the Argo workflow
#argo submit -n argo --watch $EXAMPLEDIR/argo-ml-pipeline.yml
