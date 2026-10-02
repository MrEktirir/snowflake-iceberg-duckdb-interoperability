import os
import duckdb

metadata_location = os.getenv("ICEBERG_METADATA_LOCATION")

if not metadata_location:
    raise ValueError(
        "ICEBERG_METADATA_LOCATION environment variable is not set."
    )

con = duckdb.connect()

con.execute("INSTALL iceberg;")
con.execute("LOAD iceberg;")

con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")

con.execute("""
CREATE OR REPLACE SECRET iceberg_s3_secret (
    TYPE s3,
    PROVIDER credential_chain,
    REGION 'eu-central-1'
);
""")

result = con.execute(
    f"""
    SELECT *
    FROM iceberg_scan('{metadata_location}')
    LIMIT 10
    """
).fetchdf()

print(result)