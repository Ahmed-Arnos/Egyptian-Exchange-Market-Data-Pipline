{{
  config(
    materialized='table'
  )
}}

-- Staging for index membership (which companies belong to which indices)
-- Reference data that changes infrequently
SELECT 
    im.membership_id,
    im.index_id,
    i.index_code,
    i.index_name,
    i.description as index_description,
    im.company_id,
    c.symbol,
    c.company_name,
    c.sector,
    im.weight,
    im.effective_date,
    im.is_current,
    CURRENT_TIMESTAMP() as ingested_at,
    CURRENT_TIMESTAMP() as updated_at
FROM {{ source('operational', 'TBL_INDEX_MEMBERSHIP') }} im
INNER JOIN {{ source('operational', 'TBL_INDEX') }} i 
    ON im.index_id = i.index_id
INNER JOIN {{ source('operational', 'TBL_COMPANY') }} c 
    ON im.company_id = c.company_id
WHERE im.is_current = TRUE
