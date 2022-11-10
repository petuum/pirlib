EXAMPLEDIR=$(dirname $0)
ROOTDIR=$EXAMPLEDIR/..

### Module_1: Docker_Packaging
python $ROOTDIR/bin/pircli dockerize \
    --auto $ROOTDIR \
	--pipeline example.example:infer_pipeline \
	--pipeline example.example:train_pipeline \
	--output $EXAMPLEDIR/package_argo.yml \
	--flatten

### Module_2: Argoize_Module
python  $ROOTDIR/bin/pircli argoize $EXAMPLEDIR/package_argo.yml \
	--target pirlib.backends.argo_batch:ArgoBatchBackend \
	--output $EXAMPLEDIR/argo-compose.yml

### Module_3: Argo_Execute_Module
# PYTHONPATH=$ROOTDIR $ROOTDIR/bin/pircli execute_argo $EXAMPLEDIR/argo-compose.yml \

### Execute the Argo workflow
# argo submit -n argo --watch $EXAMPLEDIR/argo-compose.yml