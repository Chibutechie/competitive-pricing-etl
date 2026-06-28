with distinct_competitors as (
    select distinct competitor_name
    from {{ ref('stg_competitor_pricing') }}
    where competitor_name is not null
),

final as (
    select
        row_number() over (order by competitor_name) as competitor_key,
        competitor_name,
        current_timestamp() as dbt_created_at,
        current_timestamp() as dbt_updated_at
    from distinct_competitors
)

select * from final