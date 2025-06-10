INSERT INTO Unit (id, address) VALUES (
    0,
    '123 Testing Lane'
) ON CONFLICT DO UPDATE SET address = excluded.address;

INSERT INTO Tenant (id, name, unit) VALUES (
    0,
    'John Testerson',
    0
) ON CONFLICT DO UPDATE SET name = excluded.name;

INSERT INTO Lease (id, tenant, rent, start_date, end_date) VALUES (
    0,
    0,
    1000,
    '2024-01-01',
    '2025-01-01'
) ON CONFLICT DO UPDATE SET tenant = excluded.tenant, rent = excluded.rent, start_date = excluded.start_date;

INSERT INTO Lease (id, tenant, rent, start_date) VALUES (
    1,
    0,
    1000,
    '2025-01-01'
) ON CONFLICT DO UPDATE SET tenant = excluded.tenant, rent = excluded.rent, start_date = excluded.start_date;

INSERT INTO CollectedRent (id, lease, amount, collected_for, collected_on) VALUES (
    1,
    1,
    400,
    '2025-02-01',
    '2025-02-05'
) ON CONFLICT DO UPDATE SET lease = excluded.lease, amount = excluded.amount, collected_on = excluded.collected_on;
