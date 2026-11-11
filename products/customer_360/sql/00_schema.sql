-- Customer 360 certified data product (D-002). Built next to the migrated estate,
-- never inside it: reads demo_redshift.silver, writes only demo_redshift.customer_360.
CREATE SCHEMA IF NOT EXISTS demo_redshift.customer_360
COMMENT 'Certified Customer 360 data product: order facts, customer profile and health, metric views. As of 2025-12-31.';
