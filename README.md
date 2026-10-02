# Snowflake Iceberg & DuckDB Interoperability

A hands-on data engineering project exploring Apache Iceberg with Snowflake-managed Iceberg tables, Dynamic Iceberg Tables, Snowpark transformations, AWS S3, and DuckDB interoperability.

## Overview

This project demonstrates an end-to-end Apache Iceberg workflow using Snowflake and AWS S3.

The workflow covers:

- Creating Snowflake-managed Iceberg tables
- Using an AWS S3 external volume for Iceberg storage
- Loading TPCH sample data into Iceberg tables
- Querying and using Time Travel with Iceberg
- Applying Row Access Policies and Masking Policies
- Building a Dynamic Iceberg Table
- Transforming Iceberg data with Snowpark
- Writing transformation results back as an Iceberg table
- Reading Snowflake-managed Iceberg data directly from AWS S3 with DuckDB

## Architecture

```text
Snowflake Sample Data
        |
        v
Snowflake-managed Iceberg Tables
        |
        |  CUSTOMER_ICEBERG
        |  ORDERS_ICEBERG
        |  NATION_ICEBERG
        |
        v
AWS S3 External Volume
        |
        v
NATION_ORDERS_ICEBERG
(Dynamic Iceberg Table)
        |
        v
Snowpark Transformation
        |
        v
CUSTOMER_VIPS_ICEBERG

AWS S3
   |
   | Iceberg metadata + Parquet
   v
DuckDB
   |
   v
Direct Iceberg Query
```

## Technologies

- Snowflake
- Apache Iceberg
- Snowpark Python
- Dynamic Tables
- DuckDB
- AWS S3
- AWS IAM
- Python

## Snowflake-Managed Iceberg Tables

The project used an AWS S3 bucket as an external volume while Snowflake managed the Iceberg catalog and metadata lifecycle.

Example:

```sql
CREATE OR REPLACE ICEBERG TABLE customer_iceberg (
    c_custkey INTEGER,
    c_name STRING,
    c_address STRING,
    c_nationkey INTEGER,
    c_phone STRING,
    c_acctbal INTEGER,
    c_mktsegment STRING,
    c_comment STRING
)
CATALOG = 'SNOWFLAKE'
EXTERNAL_VOLUME = 'iceberg_lab_vol'
BASE_LOCATION = 'iceberg_lab/iceberg_lab/customer_iceberg';
```

The table was populated from the Snowflake TPCH sample dataset.

## Dynamic Iceberg Table

A Dynamic Iceberg Table was created from customer, order, and nation Iceberg tables.

```sql
CREATE OR REPLACE DYNAMIC ICEBERG TABLE nation_orders_iceberg
    TARGET_LAG = '1 minute'
    WAREHOUSE = ICEBERG_LAB
    CATALOG = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_lab_vol'
    BASE_LOCATION = 'iceberg_lab/iceberg_lab/nation_orders_iceberg'
AS
SELECT
    n.n_regionkey AS regionkey,
    n.n_nationkey AS nationkey,
    n.n_name AS nation,
    c.c_custkey AS custkey,
    COUNT(o.o_orderkey) AS order_count,
    SUM(o.o_totalprice) AS total_price
FROM orders_iceberg o
JOIN customer_iceberg c
    ON o.o_custkey = c.c_custkey
JOIN nation_iceberg n
    ON c.c_nationkey = n.n_nationkey
GROUP BY
    n.n_regionkey,
    n.n_nationkey,
    n.n_name,
    c.c_custkey;
```

Snowflake automatically selected `FULL` refresh mode for this transformation.

## Snowpark Transformation

Snowpark was used to rank customers within each nation by total order value.

The top three customers in each nation were marked as VIP customers.

```text
NATION_ORDERS_ICEBERG
        |
        v
Snowpark DataFrame
        |
        +-- Partition by nation
        +-- Order by total_price DESC
        +-- RANK()
        +-- nation_rank <= 3
        |
        v
CUSTOMER_VIPS_ICEBERG
```

The result was written back as another Snowflake-managed Iceberg table.

## Iceberg Interoperability with DuckDB

The final part of the project demonstrated that the Iceberg data could be read by an independent query engine.

Snowflake exposed the current Iceberg metadata location:

```sql
SELECT PARSE_JSON(
    SYSTEM$GET_ICEBERG_TABLE_INFORMATION('CUSTOMER_ICEBERG')
)['metadataLocation']::VARCHAR AS METADATA_LOCATION;
```

DuckDB then accessed the Iceberg metadata and underlying Parquet files directly from S3.

```python
result = con.execute(
    f"""
    SELECT *
    FROM iceberg_scan('{metadata_location}')
    LIMIT 10
    """
).fetchdf()
```

The query does not use a Snowflake warehouse for execution.

This demonstrates one of the core benefits of an open table format:

```text
Snowflake
    |
    v
Apache Iceberg
    |
    v
AWS S3
    |
    +------> Snowflake
    |
    +------> DuckDB
```

Different query engines can operate on the same Iceberg data stored in object storage.

## Security Observation

Snowflake Row Access Policies and Masking Policies operate within Snowflake's governance layer.

When DuckDB accesses the underlying Iceberg files directly through S3, Snowflake policies are not evaluated.

Therefore, object-storage permissions are an independent security boundary and must be managed appropriately with AWS IAM.

For this project, DuckDB was given a dedicated read-only IAM identity.

## Running the DuckDB Example

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb pandas
```

Provide AWS credentials through environment variables:

```bash
export AWS_ACCESS_KEY_ID='<access-key>'
export AWS_SECRET_ACCESS_KEY='<secret-key>'
export AWS_DEFAULT_REGION='eu-central-1'
```

Provide the current Iceberg metadata location:

```bash
export ICEBERG_METADATA_LOCATION='s3://<bucket>/<path>/metadata/<metadata-file>.json'
```

Run:

```bash
python duckdb_iceberg_reader.py
```

No AWS credentials are stored in the repository.

## Key Takeaways

This project demonstrates that:

1. Snowflake can manage Apache Iceberg tables while the physical data is stored in external object storage.
2. Iceberg metadata provides a table abstraction over Parquet data files.
3. Dynamic Iceberg Tables can maintain transformation pipelines on Iceberg data.
4. Snowpark can transform Iceberg datasets and write the results back as Iceberg tables.
5. Independent query engines such as DuckDB can read the same Iceberg data directly from object storage.
6. Storage-level IAM permissions remain important because Snowflake governance policies do not apply to engines that directly access the underlying files.

## Cleanup

All Snowflake lab resources, AWS IAM resources, credentials, and S3 resources created for the project were removed after completing the tutorial.

## Reference

Snowflake Developer Guide: **Getting Started with Iceberg Tables**

This repository is a portfolio implementation based on the Snowflake tutorial, with the interoperability portion reproduced using GitHub Codespaces and DuckDB.