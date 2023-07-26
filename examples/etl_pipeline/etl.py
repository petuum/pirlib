from dataclasses import asdict
import requests
import pandas as pd
from pirlib.iotypes import DirectoryPath, FilePath
from pirlib.pipeline import pipeline
from pirlib.task import task
from pyspark.sql import SparkSession

"""
Python Extract Transform Load Pipeline Example
"""


@task
def create_spark_session(dataset: DirectoryPath) -> DirectoryPath:
    # Create a Spark session
    spark = SparkSession.builder.appName("Simple Spark Session").getOrCreate()
    # Check if the Spark session is successfully created
    print("Spark version:", spark.version)
    # Perform some simple operations using the Spark session
    data = [("Alice", 34), ("Bob", 45), ("Charlie", 29)]
    df = spark.createDataFrame(data, ["Name", "Age"])
    # Show the DataFrame
    df.show()
    # Stop the Spark session when done
    spark.stop()
    return dataset


@task
def extract_transform_load(dataset: DirectoryPath) -> DirectoryPath:
    """This API extracts data from
    http://universities.hipolabs.com
    """
    API_URL = "http://universities.hipolabs.com/search?country=United+States"
    data = requests.get(API_URL).json()

    df = pd.DataFrame(data)
    print(f"Total Number of universities from API {len(data)}")
    df = df[df["name"].str.contains("California")]
    print(f"Number of universities in california {len(df)}")
    df["domains"] = [",".join(map(str, l)) for l in df["domains"]]
    df["web_pages"] = [",".join(map(str, l)) for l in df["web_pages"]]
    df = df.reset_index(drop=True)
    df = df[["domains", "country", "web_pages", "name"]]
    outdir = task.context().output
    file_name = outdir / "file.csv"
    print(df.head)
    df.to_csv(file_name, sep="\t", encoding="utf-8")
    return outdir


@pipeline
def etl_pipeline(dataset: DirectoryPath) -> DirectoryPath:
    create_spark_session(dataset)
    data = extract_transform_load(dataset)
    return data
