# Rent App

A serverless rent collection tracker built on AWS Lambda, SQLite, and S3. Provides a web UI for recording monthly rent payments and viewing collection status across properties.

## Architecture

A single AWS Lambda function (Python 3.12, ARM64) handles all HTTP requests through a Lambda Function URL. The function serves server-side rendered HTML using Jinja2 templates -- no JavaScript framework or separate API layer for YAGNI purposes.

The database is a SQLite file stored persistently in S3. On cold start, Lambda downloads it to `/tmp`; after any write operation, the updated file is uploaded back to S3. Warm invocations reuse the cached database connection. This is a bit of an experimental approach, looking for the simplicity of SQLite in a serverless setting. However...:

**Lambda concurrency is set to 1.** This is the critical architectural constraint -- since SQLite is file-based and stored in S3, concurrent Lambda instances would each have their own copy and writes would conflict. Limiting to a single instance ensures all reads and writes go through one database file.

All AWS infrastructure is defined in Terraform (`terraform/main.tf`), including the Lambda function, S3 persistence bucket, Lambda layer (dependencies), IAM roles, and the Function URL.

An admin interface at `/admin` provides CRUD operations for managing units, tenants, leases, and collected rent records. This was the only section fully vibe-coded with Claude, in order to provide an easy self-service interface.

## Data Model

```
Unit (address)
 └── Tenant (name)
      └── Lease (rent amount, start/end dates)
           └── CollectedRent (amount, collected_for month, collected_on date)
```

- **Unit**: a rental property identified by address
- **Tenant**: an occupant assigned to a unit
- **Lease**: a rental agreement tying a tenant to a rent amount and date range (open-ended if no end date)
- **CollectedRent**: a payment record against a lease for a specific month

All entities support soft deletes via a `deleted_on` timestamp column. Schema is defined in `database/ddl.sql`.

## Request Flows

### GET `/` — View rent status

1. On cold start, download database from S3 (warm start uses cached connection)
2. Execute `get_rents.sql`: joins leases, tenants, and units; aggregates collected payments; calculates amount due and remaining per lease for the selected month
3. Render an HTML table via the `index.jinja` template showing each unit's rent status
4. Return the HTML response

### POST `/` — Record payments

1. Parse the URL-encoded form body: keys are lease IDs, values are payment amounts
2. Insert a `CollectedRent` record for each non-zero amount
3. Upload the updated database to S3
4. Return a 302 redirect back to GET (Post-Redirect-Get pattern)

## Design Decisions

**SQLite + S3 over a managed database**: For a low-traffic, single-user application, SQLite provides full ACID compliance and a relational model without the cost or complexity of RDS or DynamoDB. S3 provides durable persistence at minimal cost.

**Concurrency = 1** — The necessary tradeoff for using a file-based database. Prevents write conflicts at the cost of request throughput, which is acceptable for this use case.

**No authentication** — The Lambda Function URL is not publicly listed. Access control relies on keeping the URL private rather than an auth layer. Data here is not sensitive, and would not be an issue if it was found. There is also a CloudFront Distribution and url for this that is not in the publicly committed terraform for an easier link to bookmark.

**Soft deletes** — Records are marked with a `deleted_on` timestamp rather than removed. This preserves an audit trail and allows recovery of accidentally deleted data.

**ARM64 (Graviton)** — AWS Graviton processors offer roughly 20% cost savings over x86 with equivalent performance.

**Server-side rendering** — Jinja2 templates keep the stack simple. The UI is forms and tables; there's no need for a client-side framework or a separate API.
