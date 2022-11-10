EXAMPLEDIR=$(dirname $0)
ROOTDIR=$EXAMPLEDIR/..

### Module 1: Docker_Packaging
python $ROOTDIR/bin/pircli dockerize \
    --auto $ROOTDIR \
	--pipeline example.example:train_pipeline \
	--output $EXAMPLEDIR/package_argo.yml \
	--flatten

# Convert EXAMPLEDIR to absolute path since docker can't bind-mount relative paths.
EXAMPLEDIR=$([[ $EXAMPLEDIR = /* ]] && echo "$EXAMPLEDIR" || echo "$PWD/${EXAMPLEDIR#./}")

### Module 2: Argoize_Module
INPUT_train_dataset=$EXAMPLEDIR/inputs/train_dataset \
INPUT_translate_model=$EXAMPLEDIR/inputs/translate_model.txt \
INPUT_sentences=$EXAMPLEDIR/inputs/sentences \
OUTPUT=$EXAMPLEDIR/outputs \
NFS_SERVER=k8s-master.cm.cluster \
python  $ROOTDIR/bin/pircli argoize $EXAMPLEDIR/package_argo.yml \
	--target pirlib.backends.argo_batch:ArgoBatchBackend \
	--output $EXAMPLEDIR/argo-train.yml

### Module_3: Argo_Execute_Module
# PYTHONPATH=$ROOTDIR $ROOTDIR/bin/pircli execute_argo $EXAMPLEDIR/argo-compose.yml \

### Execute the Argo workflow
# argo submit -n argo --watch $EXAMPLEDIR/argo-compose.yml