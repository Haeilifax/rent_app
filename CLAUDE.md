# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

This project uses `uv` as the package manager and `poe` (poethepoet) as the task runner.

- `uv run poe run` - Run the app locally (STAGE=prod ISLOCAL=true)
- `uv run poe real_run` - Run the app simulating production (STAGE=prod ISLOCAL=false)
- `uv run poe dev_env` - Start interactive Python shell with database connection
- `uv run poe apply` - Deploy infrastructure changes via Terraform

## Architecture Overview

This is a serverless rent collection application with the following key components:

### Database Layer
- SQLite database with tables for Units, Tenants, Leases, and CollectedRent
    - Tenants are related to Units by Leases, and CollectedRents show the rents which have been collected against Leases (per month)
- Database is stored in S3 and downloaded to Lambda's /tmp directory on cold starts
- Uses WAL mode and optimized pragmas for performance
- Schema defined in `database/ddl.sql`

### Lambda Function (`lambda/app.py`)
- Single Lambda function handling GET/POST requests
- GET requests render an HTML form showing rent collection status
- Uses Jinja2 templates for HTML rendering
- Database connection is cached globally for warm invocations
- Concurrency limited to 1 to prevent database conflicts

### Infrastructure (`terraform/main.tf`)
- AWS Lambda function with ARM64 architecture
- S3 bucket for database persistence
- Lambda layer for Python dependencies
- Function URL for public access
- IAM roles with minimal required permissions

### Key Design Constraints
- **Concurrency = 1**: Critical for data consistency since SQLite file is stored in S3
- **Local Database vs S3 Database**: Toggle via ISLOCAL environment variable. Prefer to use the Local database in testing to avoid S3 charges
- **Single Stage**: Only "prod" stage is currently supported

### Data Flow for GET Requests
1. Lambda cold start downloads database.db from S3
2. Executes SQL query from `get_rents.sql` to get current month's rent status
3. Renders HTML using `index.jinja` template with rent data
4. Returns HTML form for rent collection

### Data Flow for POST Requests
1. Lambda cold start downloads database.db from S3
2. Parse body of `event` as JSON
3. Update CollectedRent table with new record of the rent(s) collected.
4. Store the updated SQLite db to S3
5. Redirect the requester to GET the page again (PRG flow)

## Type Checking
Pyright is configured with relaxed type checking settings in `pyrightconfig.json`. Functions should be annotated with simple type hints, to show the general signature and catch high level typing errors. Any type should only be used when the type would be too complicated to show without using Protocols or other typing structures.
