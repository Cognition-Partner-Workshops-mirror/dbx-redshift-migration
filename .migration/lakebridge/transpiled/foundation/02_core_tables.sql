-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'ZORDER'. SQLSTATE: 42601 (line 14, pos 0)

== SQL ==
EXPLAIN -- core.* landing tables: append-only raw extract, Redshift-flavored DDL.
CREATE OR REPLACE TABLE core.customers (
    customer_id         BIGINT NOT NULL,
    email STRING ,
    first_name STRING,
    last_name STRING,
    phone STRING,
    region              CHAR(4) ,
    preferred_store_id  INT,
    signup_date         DATE,
    is_business         BOOLEAN
)

ZORDER BY(customer_id);
^^^

CREATE OR REPLACE TABLE core.stores (
    store_id    INT NOT NULL,
    region      CHAR(4) ,
    store_name STRING,
    city STRING,
    state STRING
)

ZORDER BY(store_id);

CREATE OR REPLACE TABLE core.products (
    product_id      INT NOT NULL,
    sku STRING,
    product_name STRING,
    category STRING ,
    subcategory STRING,
    unit_price DECIMAL(12,2),
    cost DECIMAL(12,2),
    active          BOOLEAN
)

ZORDER BY(product_id);

CREATE OR REPLACE TABLE core.orders (
    order_id        BIGINT NOT NULL,
    customer_id     BIGINT,
    store_id        INT,
    order_ts        TIMESTAMP ,
    sales_channel STRING ,
    status STRING
)

ZORDER BY(order_ts);

CREATE OR REPLACE TABLE core.order_items (
    order_item_id   BIGINT NOT NULL,
    order_id        BIGINT,
    product_id      INT,
    quantity        INT,
    unit_price DECIMAL(12,2),
    discount DECIMAL(12,2)
)

ZORDER BY(order_id);

CREATE OR REPLACE TABLE core.payments (
    payment_id  BIGINT NOT NULL,
    order_id    BIGINT,
    method STRING,
    amount DECIMAL(12,2),
    paid_ts     TIMESTAMP
)

ZORDER BY(order_id);

CREATE OR REPLACE TABLE core.returns (
    return_id       BIGINT NOT NULL,
    order_item_id   BIGINT,
    quantity        INT,
    reason STRING,
    returned_ts     TIMESTAMP
)

ZORDER BY(returned_ts);

CREATE OR REPLACE TABLE core.shipments (
    shipment_id     BIGINT NOT NULL,
    order_id        BIGINT,
    carrier STRING ,
    ship_ts         TIMESTAMP,
    delivered_ts    TIMESTAMP
)

ZORDER BY(ship_ts);

CREATE OR REPLACE TABLE core.web_events (
    event_id     BIGINT NOT NULL,
    customer_id  BIGINT,
    event_ts     TIMESTAMP,
    event_type STRING ,
    page_url STRING
)

ZORDER BY(event_ts);

CREATE OR REPLACE TABLE core.campaign_touches (
    touch_id     BIGINT NOT NULL,
    customer_id  BIGINT,
    payload      SUPER
)

ZORDER BY(touch_id);

*/

 ---------------Exception End --------------------
