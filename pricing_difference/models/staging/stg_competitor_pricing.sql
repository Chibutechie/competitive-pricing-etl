with source as (
    select * from {{ source('pricing_difference', 'competitor_pricing') }}
),

final as (
    select 
        "comparison_id"::varchar as comparison_id
    from source
)

select * from final