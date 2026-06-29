with distinct_competitors as (
    select distinct product_name
    from {{ ref('stg_competitor_pricing') }}
    where product_name is not null
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['product_name']) }} as product_key,
        product_name,
        current_timestamp() as dbt_created_at,
        current_timestamp() as dbt_updated_at
    from distinct_competitors
)

select * from final