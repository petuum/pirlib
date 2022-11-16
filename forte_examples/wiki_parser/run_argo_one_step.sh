EXAMPLEDIR=$(dirname $0)
ROOTDIR=$EXAMPLEDIR/../..

### Module 1: Docker_Packaging
python $ROOTDIR/bin/pircli dockerize \
    --auto $ROOTDIR \
	--pipeline forte_examples.wiki_parser.one_step:wiki_parse_pipeline \
	--output $EXAMPLEDIR/one_step_argo.yml \
	--flatten