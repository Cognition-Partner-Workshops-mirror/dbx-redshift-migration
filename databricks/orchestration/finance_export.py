# Databricks notebook source
import csv
import io

from databricks.sdk.runtime import dbutils, spark

dbutils.widgets.text("catalog", "demo_redshift")
catalog = dbutils.widgets.get("catalog")
if catalog != "demo_redshift":
    raise ValueError("Only demo_redshift is allowed for this run")
spark.sql(f"USE CATALOG `{catalog}`").collect()
spark.sql("CREATE VOLUME IF NOT EXISTS gold.exports").collect()
frame = spark.sql("SELECT * FROM gold.finance_monthly ORDER BY month")
output = io.StringIO(newline="")
writer = csv.writer(output, lineterminator="\n")
writer.writerow(frame.columns)
for row in frame.toLocalIterator():
    writer.writerow(row)
directory = f"/Volumes/{catalog}/gold/exports/finance_export/monthly/as_of=2025-12-31"
dbutils.fs.mkdirs(directory)
dbutils.fs.put(f"{directory}/finance_monthly.csv", output.getvalue(), overwrite=True)
print(f"Exported {directory}/finance_monthly.csv")
