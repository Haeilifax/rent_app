SELECT
    u.address as address,
    t.name as name,
    l.rent as due,
    l.rent - coalesce(sum(cr.amount), 0) as remaining,
    l.id as lease_id
FROM Lease AS l
JOIN
    Tenant AS t ON l.tenant = t.id
JOIN
    Unit AS u ON t.unit = u.id
LEFT JOIN
    CollectedRent AS cr ON
        l.id = cr.lease
        AND cr.deleted_on IS NULL
        AND date(cr.collected_for, 'start of month') = date(:month, 'start of month')
WHERE
    l.deleted_on IS NULL
    AND date(l.start_date, 'start of month') <= date(:month, 'start of month')
    -- End of Month computation taken from https://www.sqlite.org/lang_datefunc.html
    AND ((l.end_date IS NULL) OR (date(l.end_date,'start of month','+1 month','-1 day') > date(:month, 'start of month'))) 
GROUP BY l.id -- We get to do this funky group by cause sqlite is cool
;
