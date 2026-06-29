with date_spine as (
    select dateadd(day, row_number() over (order by 1) - 1, '2024-01-01'::date) as date_day
    from table(generator(rowcount => 366))
),

final as (
    select
        date_day,
        year(date_day)::int                              as year,
        month(date_day)::int                             as month,
        day(date_day)::int                               as day,
        quarter(date_day)::int                           as quarter,
        to_varchar(date_day, 'MMMM')                     as month_name,
        to_varchar(date_day, 'MMM')                      as month_short,
        dayname(date_day)                                as day_name,
        dayofweek(date_day)::int                         as day_of_week,
        weekofyear(date_day)::int                        as week_of_year,
        case when dayofweek(date_day) in (0, 6)
             then true else false end                    as is_weekend,
        date_trunc('month', date_day)                    as first_day_of_month,
        last_day(date_day, 'month')                      as last_day_of_month,
        date_trunc('year', date_day)                     as first_day_of_year,
        date_trunc('quarter', date_day)                  as first_day_of_quarter,
        to_varchar(date_day, 'YYYYMMDD')::int            as date_key
    from date_spine
)

select * from final