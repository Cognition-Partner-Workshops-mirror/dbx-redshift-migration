-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'IMMUTABLE'. SQLSTATE: 42601 (line 6, pos 0)

== SQL ==
EXPLAIN -- SQL UDFs only (Redshift no longer allows Python UDFs).

-- Fiscal year starts Feb 1: Feb-Apr = Q1, May-Jul = Q2, Aug-Oct = Q3, Nov-Jan = Q4.
CREATE OR REPLACE FUNCTION f_fiscal_qtr(d DATE)
RETURNS STRING
IMMUTABLE
^^^
AS $$
    SELECT 'Q' || ((((EXTRACT(MONTH FROM STRING)::INT + 9) % 12) / 3) + 1)::STRING


-- Strip a phone string down to its digits.
CREATE OR REPLACE FUNCTION f_clean_phone(p STRING)
RETURNS STRING
IMMUTABLE
AS $$
    SELECT REGEXP_REPLACE(STRING, '[^0-9]', '')

*/

 ---------------Exception End --------------------
