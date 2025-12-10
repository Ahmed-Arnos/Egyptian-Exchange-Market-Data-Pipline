{{ config(materialized='view') }}

WITH raw AS (
    SELECT
        raw:"symbol"::string AS symbol,
        TO_DATE(
            NULLIF(REPLACE(raw:"date"::string, '∅', ''), ''), 
            'DY DD MON ''YY'
        ) AS date,
        TRY_TO_NUMBER(REPLACE(raw:"open"::string, '∅', ''), 38, 10)::FLOAT AS open,
        TRY_TO_NUMBER(REPLACE(raw:"high"::string, '∅', ''), 38, 10)::FLOAT AS high,
        TRY_TO_NUMBER(REPLACE(raw:"low"::string, '∅', ''), 38, 10)::FLOAT AS low,
        TRY_TO_NUMBER(REPLACE(raw:"close"::string, '∅', ''), 38, 10)::FLOAT AS close,
        TRY_TO_NUMBER(
            REGEXP_SUBSTR(
                REPLACE(raw:"change"::string, '∅', ''), 
                '([+-]?[0-9]*\\.?[0-9]+)%',           -- Captures signed decimal followed by %
                1, 1, 'e', 
                1  
            ), 38, 10
        )::FLOAT AS change_pct,
        -- FIX: Extract, multiply, and cast the volume (handling M and K)
        CASE
            -- 1. Handle Millions ('M')
            WHEN RIGHT(TRIM(REPLACE(raw:"volume"::string, '∅', '')), 1) = 'M' THEN
                -- Remove the 'M' and the non-breaking space (U+202F), then multiply by 1,000,000
                (REPLACE(REPLACE(TRIM(raw:"volume"::string), 'M', ''), ' ', ''))::float * 1000000
            
            -- 2. Handle Thousands ('K')
            WHEN RIGHT(TRIM(REPLACE(raw:"volume"::string, '∅', '')), 1) = 'K' THEN
                -- Remove the 'K' and the non-breaking space, then multiply by 1,000
                (REPLACE(REPLACE(TRIM(raw:"volume"::string), 'K', ''), ' ', ''))::float * 1000
            
            -- 3. Handle simple numbers (no suffix)
            ELSE
                -- Just remove the non-breaking space and cast it
                TRY_TO_NUMBER(REPLACE(TRIM(raw:"volume"::string), ' ', ''), 38, 10)::FLOAT
        END AS volume,
        raw:"last_day"::string AS last_day_raw,
        file_name,
        load_ts
    FROM {{ source('bronze', 'PRICES_RAW') }}
),

deduped AS (
    SELECT
        *,
        -- Assign a rank (rn) to rows partitioned by the unique keys
        -- ORDER BY load_ts DESC ensures the most recently loaded record gets rn = 1
        ROW_NUMBER() OVER (
            PARTITION BY symbol, date 
            ORDER BY load_ts DESC
        ) as rn
    FROM raw
)

SELECT symbol,
    date,
    open,
    high,
    low,
    close,
    change_pct, -- Must be here, but is protected by TRY_TO_NUMBER
    volume,
    last_day_raw,
    file_name,
    load_ts
 FROM deduped
WHERE rn = 1