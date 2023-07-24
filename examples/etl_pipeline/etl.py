from dataclasses import asdict
import requests
import pandas as pd
import yaml
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
    spark = SparkSession.builder \
        .appName("Simple Spark Session") \
        .getOrCreate()

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
    """ This API extracts data from
    http://universities.hipolabs.com
    """
    API_URL = "http://universities.hipolabs.com/search?country=United+States"
    data = requests.get(API_URL).json()
    
    df = pd.DataFrame(data)
    print(f"Total Number of universities from API {len(data)}")
    df = df[df["name"].str.contains("California")]
    print(f"Number of universities in california {len(df)}")
    df['domains'] = [','.join(map(str, l)) for l in df['domains']]
    df['web_pages'] = [','.join(map(str, l)) for l in df['web_pages']]
    df = df.reset_index(drop=True)
    df =  df[["domains","country","web_pages","name"]]
    outdir = task.context().output
    file_name = outdir / "file.csv"
    print(df.head)
    df.to_csv(file_name, sep='\t', encoding='utf-8')
    return outdir

# @task
# def transform(data:dict) -> pd.DataFrame:
#     """ Transforms the dataset into desired structure and filters"""
    

# @task
# def load(df:pd.DataFrame)-> None:
    """ Loads data into a sqllite database"""
    # disk_engine = create_engine('sqlite:///my_lite_store.db')
    # df.to_sql('cal_uni', disk_engine, if_exists='replace')

    """CREATE A CSV FILE IN OUTPUT FOLDER"""
    


@pipeline
def etl_pipeline(dataset: DirectoryPath) -> DirectoryPath:
    create_spark_session(dataset)
    data = extract_transform_load(dataset)
    return data
    # load(df)


# if __name__ == "__main__":
#     package = etl_pipeline.package()
#     print(yaml.dump(asdict(package), sort_keys=False))