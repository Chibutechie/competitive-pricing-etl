-- standardize columns, cast data types properly
with source as (
    select * from {{ source('pricing_difference', 'competitor_pricing') }}
),

final as (
    select 
        "comparison_id"::varchar as comparison_id,
        "competitor_name"::varchar as competitor_name,
        "competitor_price_ngn"::numeric(10,2) as competitor_price,
        "date_checked"::date as date_checked,
        "day_of_week"::varchar as weekdays,
        "in_stock_competitor"::boolean as in_stock_competitor,
        "is_weekend"::boolean as is_weekend,
        "loaded_at"::timestamp as loaded_at,
        "month"::int as month_num,
        "month_name"::varchar as month_name,
        "our_price_ngn"::numeric(10,2) as our_price,
        "price_difference_ngn"::numeric(10,2) as price_difference,
           case
            when "price_difference_percent" > 1 then "price_difference_percent" / 100.0
            else "price_difference_percent"
        end as percent_difference,
        "price_position"::varchar as price_position,
        "product_name"::varchar as product_name,
        "week_number"::int as week_number,
        "year"::int as year

    from source
)

select * from final