# Data

## data-sample.jsonl

The `data-sample.jsonl` file is a sample of the original arxiv dataset made available
[on Kaggle from Cornell](https://www.kaggle.com/datasets/Cornell-University/arxiv).

The sample was generated with the following bash script:

```bash
awk 'BEGIN  {srand()}
     !/^$/  { if (rand() <= .01 || FNR==1) print > "data-sample.jsonl"}' ~/Downloads/arxiv-metadata-oai-snapshot.json
```

I am sure there are smarter ways of sampling the original dataset,
I just had to do this to get something to fit into memory.

## annotation-ready.csv

The `annotation-ready.csv` file is a datetime filtered, then further random sampled,
then column subsetted dataset created to be ready for annotation.

It was produced with the `create-annotation-ready-data.py` Python file.