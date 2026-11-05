-- payment_mix: payment method mix (DECODE, NVL, NVL2).
-- Redshift NUMERIC(38,2) / NUMERIC(38,2) yields scale 4, truncated; Databricks
-- decimal division rounds, so the share is floored to 4 places (shares are >= 0).
CREATE OR REPLACE TABLE gold.payment_mix AS
SELECT COALESCE(p.method, 'unknown')                               AS method,
       DECODE(COALESCE(p.method, 'unknown'),
              'card',      'CARD',
              'cash',      'CASH',
              'wallet',    'DIGITAL',
              'gift_card', 'DIGITAL',
              'OTHER')                                             AS method_family,
       NVL2(p.method, 'captured', 'missing')                       AS method_status,
       COUNT(*)                                                    AS payment_count,
       SUM(p.amount)                                               AS amount_total,
       CAST(FLOOR(SUM(p.amount) / SUM(SUM(p.amount)) OVER (), 4)
            AS DECIMAL(38,4))                                      AS amount_share
FROM   silver.payments p
GROUP  BY p.method;
