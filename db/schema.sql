CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT,
    plan TEXT DEFAULT 'free',
    created_at TIMESTAMP
);

CREATE TABLE invoices (
    id UUID PRIMARY KEY,
    user_id UUID,
    country TEXT,
    vat_rate FLOAT,
    status TEXT,
    created_at TIMESTAMP
);
