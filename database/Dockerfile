# PostgreSQL with pgvector extension for Knowledge Aligner
FROM postgres:15

# Install build dependencies and pgvector
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    postgresql-server-dev-15 \
    && rm -rf /var/lib/apt/lists/*

# Install pgvector from source
RUN git clone https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && rm -rf /tmp/pgvector

# Copy initialization scripts
COPY schema.sql /docker-entrypoint-initdb.d/01-schema.sql
COPY seed_data.sql /docker-entrypoint-initdb.d/02-seed-data.sql

# Set default database
ENV POSTGRES_DB=knowledge_aligner
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres

# Expose PostgreSQL port
EXPOSE 5432