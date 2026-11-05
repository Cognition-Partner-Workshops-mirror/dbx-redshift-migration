-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 3, pos 0)

== SQL ==
EXPLAIN -- payment_mix: payment method mix using DECODE, NVL and NVL2.
DROP TABLE IF EXISTS mart.payment_mix;
CREATE OR REPLACE TABLE mart.payment_mix AS
^^^
SELECT COALESCE(p.method, 'unknown')                                    AS method,
       DECODE(COALESCE(p.method, 'unknown'),
              'card',      'CARD',
              'cash',      'CASH',
              'wallet',    'DIGITAL',
              'gift_card', 'DIGITAL',
              'OTHER')                                             AS method_family,
       NVL2(p.method, 'captured', 'missing')                       AS method_status,
       COUNT(*)                                                    AS payment_count,
       SUM(p.amount)                                               AS amount_total,
       SUM(p.amount) / SUM(SUM(p.amount)) OVER ()                  AS amount_share
FROM   core.payments p
GROUP  BY p.method
ORDER  BY method;

*/

 ---------------Exception End --------------------
