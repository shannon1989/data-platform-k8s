FROM metabase/metabase:v0.49.6

# copy ClickHouse Driver
ADD clickhouse.metabase-driver.jar /plugins/

# update permissions
RUN chmod 644 /plugins/clickhouse.metabase-driver.jar
