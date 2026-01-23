#!/bin/bash
# Fix PostgreSQL authentication for local development

# Modify pg_hba.conf to allow password authentication from Docker network
echo "host all all all md5" > /var/lib/postgresql/data/pg_hba.conf
echo "host all all 0.0.0.0/0 md5" >> /var/lib/postgresql/data/pg_hba.conf

# Reload PostgreSQL configuration
psql -U crypto_user -d crypto_platform -c "SELECT pg_reload_conf();"
