EXAMPLEDIR=$(dirname $0)
ROOTDIR=$EXAMPLEDIR/..

PYTHONPATH=$ROOTDIR $ROOTDIR/bin/pircli package \
	--pipeline example.example:infer_pipeline \
	--pipeline example.example:train_pipeline \
	--output $EXAMPLEDIR/package_inproc.yml

PYTHONPATH=$ROOTDIR $ROOTDIR/bin/pircli execute \
	$EXAMPLEDIR/package_inproc.yml train_pipeline \
	--target pirlib.backends.inproc:InprocBackend \
	--input train_dataset=$EXAMPLEDIR/inputs/train_dataset \
	--input translate_model=$EXAMPLEDIR/inputs/translate_model.txt \
	--input sentences=$EXAMPLEDIR/inputs/sentences \
	--output 0=$EXAMPLEDIR/outputs/0 \
	--output 1=$EXAMPLEDIR/outputs/1
