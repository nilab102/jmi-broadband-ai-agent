import psycopg2

conn = psycopg2.connect("postgresql://postgres.jluuralqpnexhxlcuewz:HIiamjami1234@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres")
cursor = conn.cursor()

# Get table structure
cursor.execute("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_name = 'postal_code'
    ORDER BY ordinal_position;
""")

print("\nTable: postal_code")
print("-" * 60)
print(f"{'Column Name':<20} {'Data Type':<20} {'Max Length':<15}")
print("-" * 60)
for row in cursor.fetchall():
    col_name, data_type, max_len = row
    max_len_str = str(max_len) if max_len else 'N/A'
    print(f"{col_name:<20} {data_type:<20} {max_len_str:<15}")

# Get sample data
cursor.execute("SELECT * FROM postal_code LIMIT 5;")
print("\n\nSample data:")
print("-" * 60)
for row in cursor.fetchall():
    print(row)

# Get total count
cursor.execute("SELECT COUNT(*) FROM postal_code;")
count = cursor.fetchone()[0]
print(f"\n\nTotal records: {count:,}")

cursor.close()
conn.close()

