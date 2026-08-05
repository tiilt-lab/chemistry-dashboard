#!/usr/bin/env python3
"""
Verification script to check the state of foreign key constraints in the database.
This helps verify before and after running migrations.

Usage: python verify_foreign_keys.py
"""

from app import app, db
import sqlalchemy as sa

def check_foreign_keys():
    """Check and display all foreign key constraints for transcript tables"""

    with app.app_context():
        inspector = sa.inspect(db.engine)

        tables_to_check = ['transcript', 'concept_session', 'speaker']

        results = []

        for table_name in tables_to_check:
            try:
                foreign_keys = inspector.get_foreign_keys(table_name)

                for fk in foreign_keys:
                    constraint_name = fk.get('name', 'unnamed')
                    constrained_cols = ', '.join(fk.get('constrained_columns', []))
                    referred_table = fk.get('referred_table', '')
                    referred_cols = ', '.join(fk.get('referred_columns', []))

                    # Get ondelete action (defaults to RESTRICT if not specified)
                    options = fk.get('options', {})
                    ondelete = options.get('ondelete', 'RESTRICT')

                    results.append([
                        table_name,
                        constraint_name,
                        constrained_cols,
                        f"{referred_table}.{referred_cols}",
                        ondelete
                    ])

            except Exception as e:
                results.append([table_name, 'ERROR', str(e), '', ''])

        # Display results in a nice table
        headers = ['Table', 'Constraint Name', 'Column', 'References', 'On Delete']
        print("\n=== Foreign Key Constraints ===\n")

        # Print header
        print(f"{'Table':<20} {'Constraint Name':<25} {'Column':<25} {'References':<30} {'On Delete':<15}")
        print("-" * 115)

        # Print rows
        for row in results:
            table, constraint, col, ref, ondelete = row
            print(f"{table:<20} {constraint:<25} {col:<25} {ref:<30} {ondelete:<15}")

        # Highlight which ones need CASCADE
        print("\n=== Analysis ===\n")

        for row in results:
            table_name, constraint_name, col, ref, ondelete = row
            if table_name in ['transcript']:
                if ondelete != 'CASCADE':
                    print(f"⚠️  {table_name}.{col} -> {ref}: Currently {ondelete}, needs CASCADE")
                else:
                    print(f"✅ {table_name}.{col} -> {ref}: Already has CASCADE")
            elif ondelete == 'CASCADE':
                print(f"✅ {table_name}.{col} -> {ref}: Has CASCADE (for reference)")

        # SQL commands to fix manually if needed
        print("\n=== Manual SQL Fix (if migration fails) ===\n")
        print("If the migration fails, you can run these commands manually in MySQL:")
        print()

        for row in results:
            table_name, constraint_name, col, ref, ondelete = row
            if table_name in ['transcript'] and ondelete != 'CASCADE':
                print(f"-- Fix {table_name}")
                print(f"ALTER TABLE {table_name} DROP FOREIGN KEY {constraint_name};")
                referred_table = ref.split('.')[0]
                referred_col = ref.split('.')[1]
                print(f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name}")
                print(f"  FOREIGN KEY ({col}) REFERENCES {referred_table}({referred_col})")
                print(f"  ON DELETE CASCADE;")
                print()

if __name__ == '__main__':
    print("Checking foreign key constraints...")
    check_foreign_keys()
    print("\nDone!")