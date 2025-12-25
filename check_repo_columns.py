import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blt.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT column_name, column_default, is_nullable, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'website_repo' AND is_nullable = 'NO' 
    ORDER BY ordinal_position
""")

print("NOT NULL columns in website_repo:")
print("-" * 80)
for row in cursor.fetchall():
    default = str(row[1]) if row[1] else "None"
    print(f"{row[0]:30} | Default: {default:20} | Type: {row[3]}")
