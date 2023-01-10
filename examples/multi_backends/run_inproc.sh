EXAMPLEDIR=$(dirname $0)
ROOTDIR=$EXAMPLEDIR/../..

PYTHONPATH=$ROOTDIR $ROOTDIR/bin/pircli package \
	--pipeline examples.multi_backends.example:infer_pipeline \
	--pipeline examples.multi_backends.example:train_pipeline \
	--output $EXAMPLEDIR/package_inproc.yml

PYTHONPATH=$ROOTDIR $ROOTDIR/bin/pircli execute \
	$EXAMPLEDIR/package_inproc.yml train_pipeline \
	--target pirlib.backends.inproc:InprocBackend \
	--input train_dataset=$EXAMPLEDIR/inputs/train_dataset \
	--input translate_model=$EXAMPLEDIR/inputs/translate_model.txt \
	--input sentences=$EXAMPLEDIR/inputs/sentences \
	--output return.0=$EXAMPLEDIR/outputs/return.0 \
	--output return.1=$EXAMPLEDIR/outputs/return.1
