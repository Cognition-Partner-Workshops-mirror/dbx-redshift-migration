-- Foundation: Redshift core layer rebuilt on Databricks SQL.
--
-- Bronze: the ten raw seed extracts in /Volumes/<current catalog>/bronze/raw
-- loaded as-is (every column STRING, source column order, \N -> NULL).
-- Silver: typed tables mirroring legacy/redshift/00_foundation/02_core_tables.sql
-- (core.x -> silver.x) plus the two SQL UDFs from 03_udfs.sql.
--
-- Type mapping: VARCHAR(n)/CHAR(n)/INT/BIGINT/NUMERIC(p,s)/DATE/BOOLEAN keep
-- their Redshift types; TIMESTAMP (without time zone) -> TIMESTAMP_NTZ; SUPER
-- -> STRING holding the original JSON text (query with payload:path or
-- from_json). CHAR(4) values are stored blank-padded because Databricks does
-- not pad CHAR on write or read, while Redshift returns the padded value.
-- DISTKEY/SORTKEY/DISTSTYLE/ENCODE are dropped; fact tables use liquid
-- clustering on their former distribution/sort keys.
-- Paths come from current_catalog(); the harness sets the catalog context.

-- ---------------------------------------------------------------- bronze

BEGIN
  DECLARE src STRING DEFAULT '/Volumes/' || current_catalog() || '/bronze/raw/customers.csv';
  EXECUTE IMMEDIATE
    'CREATE OR REPLACE TABLE bronze.customers
       COMMENT \'Raw seed extract customers.csv loaded as-is\'
     AS SELECT customer_id, email, first_name, last_name, phone, region, preferred_store_id, signup_date, is_business
     FROM read_files(:src, format => \'csv\', header => true, inferSchema => false,
                     quote => \'"\', escape => \'"\', nullValue => \'\\\\N\',
                     mode => \'FAILFAST\', schema => \'customer_id STRING, email STRING, first_name STRING, last_name STRING, phone STRING, region STRING, preferred_store_id STRING, signup_date STRING, is_business STRING\')'
    USING src AS src;
END;

BEGIN
  DECLARE src STRING DEFAULT '/Volumes/' || current_catalog() || '/bronze/raw/stores.csv';
  EXECUTE IMMEDIATE
    'CREATE OR REPLACE TABLE bronze.stores
       COMMENT \'Raw seed extract stores.csv loaded as-is\'
     AS SELECT store_id, region, store_name, city, state
     FROM read_files(:src, format => \'csv\', header => true, inferSchema => false,
                     quote => \'"\', escape => \'"\', nullValue => \'\\\\N\',
                     mode => \'FAILFAST\', schema => \'store_id STRING, region STRING, store_name STRING, city STRING, state STRING\')'
    USING src AS src;
END;

BEGIN
  DECLARE src STRING DEFAULT '/Volumes/' || current_catalog() || '/bronze/raw/products.csv';
  EXECUTE IMMEDIATE
    'CREATE OR REPLACE TABLE bronze.products
       COMMENT \'Raw seed extract products.csv loaded as-is\'
     AS SELECT product_id, sku, product_name, category, subcategory, unit_price, cost, active
     FROM read_files(:src, format => \'csv\', header => true, inferSchema => false,
                     quote => \'"\', escape => \'"\', nullValue => \'\\\\N\',
                     mode => \'FAILFAST\', schema => \'product_id STRING, sku STRING, product_name STRING, category STRING, subcategory STRING, unit_price STRING, cost STRING, active STRING\')'
    USING src AS src;
END;

BEGIN
  DECLARE src STRING DEFAULT '/Volumes/' || current_catalog() || '/bronze/raw/orders.csv';
  EXECUTE IMMEDIATE
    'CREATE OR REPLACE TABLE bronze.orders
       COMMENT \'Raw seed extract orders.csv loaded as-is\'
     AS SELECT order_id, customer_id, store_id, order_ts, sales_channel, status
     FROM read_files(:src, format => \'csv\', header => true, inferSchema => false,
                     quote => \'"\', escape => \'"\', nullValue => \'\\\\N\',
                     mode => \'FAILFAST\', schema => \'order_id STRING, customer_id STRING, store_id STRING, order_ts STRING, sales_channel STRING, status STRING\')'
    USING src AS src;
END;

BEGIN
  DECLARE src STRING DEFAULT '/Volumes/' || current_catalog() || '/bronze/raw/order_items.csv';
  EXECUTE IMMEDIATE
    'CREATE OR REPLACE TABLE bronze.order_items
       COMMENT \'Raw seed extract order_items.csv loaded as-is\'
     AS SELECT order_item_id, order_id, product_id, quantity, unit_price, discount
     FROM read_files(:src, format => \'csv\', header => true, inferSchema => false,
                     quote => \'"\', escape => \'"\', nullValue => \'\\\\N\',
                     mode => \'FAILFAST\', schema => \'order_item_id STRING, order_id STRING, product_id STRING, quantity STRING, unit_price STRING, discount STRING\')'
    USING src AS src;
END;

BEGIN
  DECLARE src STRING DEFAULT '/Volumes/' || current_catalog() || '/bronze/raw/payments.csv';
  EXECUTE IMMEDIATE
    'CREATE OR REPLACE TABLE bronze.payments
       COMMENT \'Raw seed extract payments.csv loaded as-is\'
     AS SELECT payment_id, order_id, method, amount, paid_ts
     FROM read_files(:src, format => \'csv\', header => true, inferSchema => false,
                     quote => \'"\', escape => \'"\', nullValue => \'\\\\N\',
                     mode => \'FAILFAST\', schema => \'payment_id STRING, order_id STRING, method STRING, amount STRING, paid_ts STRING\')'
    USING src AS src;
END;

BEGIN
  DECLARE src STRING DEFAULT '/Volumes/' || current_catalog() || '/bronze/raw/returns.csv';
  EXECUTE IMMEDIATE
    'CREATE OR REPLACE TABLE bronze.returns
       COMMENT \'Raw seed extract returns.csv loaded as-is\'
     AS SELECT return_id, order_item_id, quantity, reason, returned_ts
     FROM read_files(:src, format => \'csv\', header => true, inferSchema => false,
                     quote => \'"\', escape => \'"\', nullValue => \'\\\\N\',
                     mode => \'FAILFAST\', schema => \'return_id STRING, order_item_id STRING, quantity STRING, reason STRING, returned_ts STRING\')'
    USING src AS src;
END;

BEGIN
  DECLARE src STRING DEFAULT '/Volumes/' || current_catalog() || '/bronze/raw/shipments.csv';
  EXECUTE IMMEDIATE
    'CREATE OR REPLACE TABLE bronze.shipments
       COMMENT \'Raw seed extract shipments.csv loaded as-is\'
     AS SELECT shipment_id, order_id, carrier, ship_ts, delivered_ts
     FROM read_files(:src, format => \'csv\', header => true, inferSchema => false,
                     quote => \'"\', escape => \'"\', nullValue => \'\\\\N\',
                     mode => \'FAILFAST\', schema => \'shipment_id STRING, order_id STRING, carrier STRING, ship_ts STRING, delivered_ts STRING\')'
    USING src AS src;
END;

BEGIN
  DECLARE src STRING DEFAULT '/Volumes/' || current_catalog() || '/bronze/raw/web_events.csv';
  EXECUTE IMMEDIATE
    'CREATE OR REPLACE TABLE bronze.web_events
       COMMENT \'Raw seed extract web_events.csv loaded as-is\'
     AS SELECT event_id, customer_id, event_ts, event_type, page_url
     FROM read_files(:src, format => \'csv\', header => true, inferSchema => false,
                     quote => \'"\', escape => \'"\', nullValue => \'\\\\N\',
                     mode => \'FAILFAST\', schema => \'event_id STRING, customer_id STRING, event_ts STRING, event_type STRING, page_url STRING\')'
    USING src AS src;
END;

BEGIN
  DECLARE src STRING DEFAULT '/Volumes/' || current_catalog() || '/bronze/raw/campaign_touches.csv';
  EXECUTE IMMEDIATE
    'CREATE OR REPLACE TABLE bronze.campaign_touches
       COMMENT \'Raw seed extract campaign_touches.csv loaded as-is\'
     AS SELECT touch_id, customer_id, payload
     FROM read_files(:src, format => \'csv\', header => true, inferSchema => false,
                     quote => \'"\', escape => \'"\', nullValue => \'\\\\N\',
                     mode => \'FAILFAST\', schema => \'touch_id STRING, customer_id STRING, payload STRING\')'
    USING src AS src;
END;

-- ---------------------------------------------------------------- UDFs
-- Same expression as Redshift: 'Q' || (((month + 9) % 12) / 3 + 1) with integer
-- division (div), so Mar-May = Q1, Jun-Aug = Q2, Sep-Nov = Q3, Dec-Feb = Q4.
-- NULL in -> NULL out.
CREATE OR REPLACE FUNCTION silver.f_fiscal_qtr(d DATE)
RETURNS STRING
DETERMINISTIC
COMMENT 'Port of Redshift f_fiscal_qtr: fiscal quarter label Q1-Q4 (FY starts Feb 1)'
RETURN 'Q' || CAST(div((EXTRACT(MONTH FROM d) + 9) % 12, 3) + 1 AS STRING);

-- Strip a phone string down to its digits; NULL in -> NULL out.
CREATE OR REPLACE FUNCTION silver.f_clean_phone(p STRING)
RETURNS STRING
DETERMINISTIC
COMMENT 'Port of Redshift f_clean_phone: digits only'
RETURN regexp_replace(p, '[^0-9]', '');

-- ---------------------------------------------------------------- silver

CREATE OR REPLACE TABLE silver.customers (
    customer_id         BIGINT NOT NULL,
    email               VARCHAR(320),
    first_name          VARCHAR(64),
    last_name           VARCHAR(64),
    phone               VARCHAR(32),
    region              CHAR(4),
    preferred_store_id  INT,
    signup_date         DATE,
    is_business         BOOLEAN
)
CLUSTER BY (customer_id)
COMMENT 'Typed core.customers from bronze.customers';

INSERT OVERWRITE silver.customers
SELECT CAST(customer_id AS BIGINT) AS customer_id,
       CAST(email AS VARCHAR(320)) AS email,
       CAST(first_name AS VARCHAR(64)) AS first_name,
       CAST(last_name AS VARCHAR(64)) AS last_name,
       CAST(phone AS VARCHAR(32)) AS phone,
       CAST(concat(region, repeat(' ', 4 - length(region))) AS CHAR(4)) AS region,
       CAST(preferred_store_id AS INT) AS preferred_store_id,
       CAST(signup_date AS DATE) AS signup_date,
       CAST(is_business AS BOOLEAN) AS is_business
FROM   bronze.customers;

CREATE OR REPLACE TABLE silver.stores (
    store_id    INT NOT NULL,
    region      CHAR(4),
    store_name  VARCHAR(64),
    city        VARCHAR(64),
    state       VARCHAR(2)
)
COMMENT 'Typed core.stores from bronze.stores';

INSERT OVERWRITE silver.stores
SELECT CAST(store_id AS INT) AS store_id,
       CAST(concat(region, repeat(' ', 4 - length(region))) AS CHAR(4)) AS region,
       CAST(store_name AS VARCHAR(64)) AS store_name,
       CAST(city AS VARCHAR(64)) AS city,
       CAST(state AS VARCHAR(2)) AS state
FROM   bronze.stores;

CREATE OR REPLACE TABLE silver.products (
    product_id    INT NOT NULL,
    sku           VARCHAR(16),
    product_name  VARCHAR(128),
    category      VARCHAR(32),
    subcategory   VARCHAR(32),
    unit_price    DECIMAL(12,2),
    cost          DECIMAL(12,2),
    active        BOOLEAN
)
COMMENT 'Typed core.products from bronze.products';

INSERT OVERWRITE silver.products
SELECT CAST(product_id AS INT) AS product_id,
       CAST(sku AS VARCHAR(16)) AS sku,
       CAST(product_name AS VARCHAR(128)) AS product_name,
       CAST(category AS VARCHAR(32)) AS category,
       CAST(subcategory AS VARCHAR(32)) AS subcategory,
       CAST(unit_price AS DECIMAL(12,2)) AS unit_price,
       CAST(cost AS DECIMAL(12,2)) AS cost,
       CAST(active AS BOOLEAN) AS active
FROM   bronze.products;

CREATE OR REPLACE TABLE silver.orders (
    order_id       BIGINT NOT NULL,
    customer_id    BIGINT,
    store_id       INT,
    order_ts       TIMESTAMP_NTZ,
    sales_channel  VARCHAR(16),
    status         VARCHAR(16)
)
CLUSTER BY (customer_id, order_ts)
COMMENT 'Typed core.orders from bronze.orders';

INSERT OVERWRITE silver.orders
SELECT CAST(order_id AS BIGINT) AS order_id,
       CAST(customer_id AS BIGINT) AS customer_id,
       CAST(store_id AS INT) AS store_id,
       CAST(order_ts AS TIMESTAMP_NTZ) AS order_ts,
       CAST(sales_channel AS VARCHAR(16)) AS sales_channel,
       CAST(status AS VARCHAR(16)) AS status
FROM   bronze.orders;

CREATE OR REPLACE TABLE silver.order_items (
    order_item_id  BIGINT NOT NULL,
    order_id       BIGINT,
    product_id     INT,
    quantity       INT,
    unit_price     DECIMAL(12,2),
    discount       DECIMAL(12,2)
)
CLUSTER BY (order_id)
COMMENT 'Typed core.order_items from bronze.order_items';

INSERT OVERWRITE silver.order_items
SELECT CAST(order_item_id AS BIGINT) AS order_item_id,
       CAST(order_id AS BIGINT) AS order_id,
       CAST(product_id AS INT) AS product_id,
       CAST(quantity AS INT) AS quantity,
       CAST(unit_price AS DECIMAL(12,2)) AS unit_price,
       CAST(discount AS DECIMAL(12,2)) AS discount
FROM   bronze.order_items;

CREATE OR REPLACE TABLE silver.payments (
    payment_id  BIGINT NOT NULL,
    order_id    BIGINT,
    method      VARCHAR(16),
    amount      DECIMAL(12,2),
    paid_ts     TIMESTAMP_NTZ
)
CLUSTER BY (order_id)
COMMENT 'Typed core.payments from bronze.payments';

INSERT OVERWRITE silver.payments
SELECT CAST(payment_id AS BIGINT) AS payment_id,
       CAST(order_id AS BIGINT) AS order_id,
       CAST(method AS VARCHAR(16)) AS method,
       CAST(amount AS DECIMAL(12,2)) AS amount,
       CAST(paid_ts AS TIMESTAMP_NTZ) AS paid_ts
FROM   bronze.payments;

CREATE OR REPLACE TABLE silver.returns (
    return_id      BIGINT NOT NULL,
    order_item_id  BIGINT,
    quantity       INT,
    reason         VARCHAR(64),
    returned_ts    TIMESTAMP_NTZ
)
CLUSTER BY (order_item_id, returned_ts)
COMMENT 'Typed core.returns from bronze.returns';

INSERT OVERWRITE silver.returns
SELECT CAST(return_id AS BIGINT) AS return_id,
       CAST(order_item_id AS BIGINT) AS order_item_id,
       CAST(quantity AS INT) AS quantity,
       CAST(reason AS VARCHAR(64)) AS reason,
       CAST(returned_ts AS TIMESTAMP_NTZ) AS returned_ts
FROM   bronze.returns;

CREATE OR REPLACE TABLE silver.shipments (
    shipment_id   BIGINT NOT NULL,
    order_id      BIGINT,
    carrier       VARCHAR(16),
    ship_ts       TIMESTAMP_NTZ,
    delivered_ts  TIMESTAMP_NTZ
)
CLUSTER BY (order_id, ship_ts)
COMMENT 'Typed core.shipments from bronze.shipments';

INSERT OVERWRITE silver.shipments
SELECT CAST(shipment_id AS BIGINT) AS shipment_id,
       CAST(order_id AS BIGINT) AS order_id,
       CAST(carrier AS VARCHAR(16)) AS carrier,
       CAST(ship_ts AS TIMESTAMP_NTZ) AS ship_ts,
       CAST(delivered_ts AS TIMESTAMP_NTZ) AS delivered_ts
FROM   bronze.shipments;

CREATE OR REPLACE TABLE silver.web_events (
    event_id     BIGINT NOT NULL,
    customer_id  BIGINT,
    event_ts     TIMESTAMP_NTZ,
    event_type   VARCHAR(16),
    page_url     VARCHAR(256)
)
CLUSTER BY (customer_id, event_ts)
COMMENT 'Typed core.web_events from bronze.web_events';

INSERT OVERWRITE silver.web_events
SELECT CAST(event_id AS BIGINT) AS event_id,
       CAST(customer_id AS BIGINT) AS customer_id,
       CAST(event_ts AS TIMESTAMP_NTZ) AS event_ts,
       CAST(event_type AS VARCHAR(16)) AS event_type,
       CAST(page_url AS VARCHAR(256)) AS page_url
FROM   bronze.web_events;

CREATE OR REPLACE TABLE silver.campaign_touches (
    touch_id     BIGINT NOT NULL,
    customer_id  BIGINT,
    payload      STRING
)
CLUSTER BY (customer_id, touch_id)
COMMENT 'Typed core.campaign_touches from bronze.campaign_touches';

INSERT OVERWRITE silver.campaign_touches
SELECT CAST(touch_id AS BIGINT) AS touch_id,
       CAST(customer_id AS BIGINT) AS customer_id,
       payload
FROM   bronze.campaign_touches;
