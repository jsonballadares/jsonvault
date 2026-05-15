"""
Generic Postgres Query Tool

Read-only query interface to a single Postgres database. Used by the
`/query-db` skill to introspect schema and answer questions.

Connection details come from a sibling `.env` file (see `.env.example`).

Usage:
    python query.py --schema                     # Print all tables and columns
    python query.py --sql "SELECT ..."           # Run a read-only SQL query
    python query.py --sql "SELECT ..." --csv     # Output as CSV instead of table
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SCHEMA = os.environ.get("DB_SCHEMA", "public")


def get_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        options="-c statement_timeout=30000",  # 30s timeout
    )


def print_schema(conn):
    """Print all tables and their columns in the configured schema."""
    query = """
        SELECT
            t.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable
        FROM information_schema.tables t
        JOIN information_schema.columns c
            ON c.table_schema = t.table_schema
            AND c.table_name = t.table_name
        WHERE t.table_schema = %s
            AND t.table_type = 'BASE TABLE'
        ORDER BY t.table_name, c.ordinal_position;
    """
    with conn.cursor() as cur:
        cur.execute(query, (SCHEMA,))
        rows = cur.fetchall()

    if not rows:
        print(f"No tables found in schema '{SCHEMA}'.")
        return

    current_table = None
    for table_name, col_name, data_type, nullable in rows:
        if table_name != current_table:
            if current_table is not None:
                print()
            print(f"=== {table_name} ===")
            current_table = table_name
        null_marker = "" if nullable == "YES" else " NOT NULL"
        print(f"  {col_name}: {data_type}{null_marker}")


def run_query(conn, sql, output_csv=False):
    """Execute a read-only SQL query and print results."""
    blocked = sql.strip().upper()
    for keyword in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"):
        if blocked.startswith(keyword):
            print(f"Error: {keyword} statements are not allowed (read-only).", file=sys.stderr)
            sys.exit(1)

    with conn.cursor() as cur:
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    if output_csv:
        writer = csv.writer(sys.stdout)
        writer.writerow(columns)
        writer.writerows(rows)
    else:
        col_widths = [len(c) for c in columns]
        str_rows = []
        for row in rows:
            str_row = [str(v) if v is not None else "NULL" for v in row]
            str_rows.append(str_row)
            for i, val in enumerate(str_row):
                col_widths[i] = max(col_widths[i], len(val))

        header = " | ".join(c.ljust(w) for c, w in zip(columns, col_widths))
        print(header)
        print("-+-".join("-" * w for w in col_widths))

        for str_row in str_rows:
            print(" | ".join(v.ljust(w) for v, w in zip(str_row, col_widths)))

        print(f"\n({len(rows)} rows)")


def main():
    parser = argparse.ArgumentParser(description="Read-only Postgres query tool.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--schema", action="store_true", help="Print database schema")
    group.add_argument("--sql", type=str, help="SQL query to execute (read-only)")
    parser.add_argument("--csv", action="store_true", help="Output results as CSV")

    args = parser.parse_args()

    conn = get_connection()
    try:
        conn.set_session(readonly=True)
        if args.schema:
            print_schema(conn)
        elif args.sql:
            run_query(conn, args.sql, output_csv=args.csv)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
