"""
Data Loading Script for Clinical Supply Chain AI

This script loads CSV files into the PostgreSQL database.
Place all CSV files in the database/data/ directory before running.
"""

import psycopg2
import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List
import glob

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "clinical_supply_chain")

DATA_DIR = Path(__file__).parent.parent / "data"


# Mapping of CSV file patterns to table names
TABLE_MAPPINGS = {
    "allocated_materials": ["allocated", "allocation", "reserved"],
    "available_inventory_report": ["available", "inventory_report"],
    "enrollment_rate_report": ["enrollment_rate", "enrollment"],
    "country_level_enrollment": ["country_enrollment", "country_level"],
    "affiliate_warehouse_inventory": ["warehouse", "affiliate"],
    "re_evaluation": ["reeval", "re-evaluation", "shelf_life"],
    "rim": ["regulatory", "rim"],
    "material_country_requirements": ["requirements", "country_req"],
    "ip_shipping_timelines": ["shipping", "timeline", "logistics"],
    "distribution_order_report": ["distribution", "order", "shipment"],
    "qdocs": ["qdoc", "quality", "document"],
    "trials_metadata": ["trial", "study"]
}


def find_csv_files() -> Dict[str, Path]:
    """
    Find CSV files in the data directory and map them to tables.
    """
    print(f"Searching for CSV files in {DATA_DIR}...")
    
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created data directory: {DATA_DIR}")
    
    csv_files = list(DATA_DIR.glob("*.csv"))
    
    if not csv_files:
        print(f"\n⚠️  No CSV files found in {DATA_DIR}")
        print("Please place your CSV files in this directory and run again.")
        return {}
    
    print(f"✓ Found {len(csv_files)} CSV file(s)")
    
    # Map CSV files to tables
    file_mapping = {}
    
    for csv_file in csv_files:
        filename_lower = csv_file.stem.lower()
        
        # Try to match to a table
        matched = False
        for table_name, patterns in TABLE_MAPPINGS.items():
            if any(pattern in filename_lower for pattern in patterns):
                file_mapping[table_name] = csv_file
                matched = True
                print(f"  - {csv_file.name} → {table_name}")
                break
        
        if not matched:
            print(f"  - {csv_file.name} → (unmatched, will skip)")
    
    return file_mapping


def clean_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """
    Clean and prepare DataFrame for database insertion.
    """
    # Convert column names to lowercase with underscores
    df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
    
    # Handle common data issues
    # Replace empty strings with None for database NULL
    df = df.replace('', None)
    df = df.replace('NA', None)
    df = df.replace('N/A', None)
    
    # Convert date columns
    date_columns = [col for col in df.columns if 'date' in col]
    for col in date_columns:
        try:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        except Exception as e:
            print(f"    Warning: Could not convert {col} to date: {e}")
    
    # Remove completely empty rows
    df = df.dropna(how='all')
    
    return df


def load_csv_to_table(csv_path: Path, table_name: str, conn):
    """
    Load a CSV file into a PostgreSQL table.
    """
    print(f"\nLoading {csv_path.name} into table '{table_name}'...")
    
    try:
        # Read CSV
        df = pd.read_csv(csv_path)
        print(f"  ✓ Read CSV: {len(df)} rows, {len(df.columns)} columns")
        
        # Clean data
        df = clean_dataframe(df, table_name)
        print(f"  ✓ Cleaned data: {len(df)} rows after cleaning")
        
        if df.empty:
            print(f"  ⚠️  No data to load (empty after cleaning)")
            return
        
        # Get table columns from database
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            AND column_name NOT IN ('id', 'created_at', 'updated_at')
            ORDER BY ordinal_position;
        """)
        db_columns = [row[0] for row in cursor.fetchall()]
        
        # Match DataFrame columns to database columns
        matching_columns = [col for col in df.columns if col in db_columns]
        
        if not matching_columns:
            print(f"  ✗ No matching columns found between CSV and table")
            print(f"    CSV columns: {list(df.columns)[:10]}")
            print(f"    DB columns: {db_columns[:10]}")
            return
        
        print(f"  ✓ Matched {len(matching_columns)} columns")
        
        # Prepare data for insertion
        df_to_insert = df[matching_columns]
        
        # Clear existing data (optional - comment out if you want to append)
        cursor.execute(f"DELETE FROM {table_name};")
        print(f"  ✓ Cleared existing data from {table_name}")
        
        # Insert data using pandas to_sql (fast and efficient)
        from sqlalchemy import create_engine
        
        engine = create_engine(
            f"postgresql://{DB_USER}:{DB_PASSWORD}@"
            f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
        
        df_to_insert.to_sql(
            table_name,
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        
        print(f"  ✓ Successfully loaded {len(df_to_insert)} rows into {table_name}")
        
        # Verify
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"  ✓ Verification: Table now has {count} rows")
        
        cursor.close()
        
    except Exception as e:
        print(f"  ✗ Error loading {csv_path.name}: {e}")
        raise


def main():
    print("=" * 60)
    print("Clinical Supply Chain AI - Data Loading")
    print("=" * 60)
    
    # Find CSV files
    file_mapping = find_csv_files()
    
    if not file_mapping:
        print("\n⚠️  No CSV files to load. Exiting.")
        return
    
    print(f"\nPreparing to load {len(file_mapping)} tables...")
    input("Press Enter to continue or Ctrl+C to cancel...")
    
    # Connect to database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )
    conn.autocommit = True
    
    # Load each file
    success_count = 0
    failed_count = 0
    
    for table_name, csv_path in file_mapping.items():
        try:
            load_csv_to_table(csv_path, table_name, conn)
            success_count += 1
        except Exception as e:
            print(f"✗ Failed to load {table_name}: {e}")
            failed_count += 1
    
    conn.close()
    
    # Summary
    print("\n" + "=" * 60)
    print("Data Loading Summary")
    print("=" * 60)
    print(f"✓ Successfully loaded: {success_count} tables")
    if failed_count > 0:
        print(f"✗ Failed to load: {failed_count} tables")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Run: python database/setup/verify_data.py")
    print("2. Start the agents: python agents/supply_watchdog/run_monitoring.py")


if __name__ == "__main__":
    main()
