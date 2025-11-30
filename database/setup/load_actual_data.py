"""
Comprehensive Data Loader for Actual CSV Files
Handles all 40+ tables with intelligent mapping and transformation
"""

import pandas as pd
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from datetime import datetime
import re

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname": os.getenv("DB_NAME", "clinical_supply_chain"),
}

DATA_DIR = Path(__file__).parent.parent / "data"


def parse_timeline(timeline_str):
    """Extract days from timeline string like '6 days door-to-door'"""
    match = re.search(r'(\d+)\s*days?', str(timeline_str))
    return int(match.group(1)) if match else None


def load_allocated_materials_to_orders():
    """Load allocated materials to orders"""
    file_path = DATA_DIR / "allocated_materials_to_orders.csv"
    if not file_path.exists():
        print(f"⚠️  {file_path.name} not found")
        return
    
    df = pd.read_csv(file_path)
    df['modified_date'] = pd.to_datetime(df['modified_date'], errors='coerce')
    
    engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    df.to_sql('allocated_materials_to_orders', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"✓ Loaded {len(df)} rows into allocated_materials_to_orders")


def load_available_inventory():
    """Load available inventory report"""
    file_path = DATA_DIR / "available_inventory_report.csv"
    if not file_path.exists():
        print(f"⚠️  {file_path.name} not found")
        return
    
    df = pd.read_csv(file_path)
    
    # Rename columns to match schema
    df.columns = [
        'trial_name', 'location', 'investigator', 'package_type_description',
        'lot', 'expiry_date', 'packages_awaiting', 'received_packages',
        'packages_pending_ffu', 'packages_pending_shipment', 'shipped_packages',
        'min_qty', 'max_qty', 'initial_qty'
    ]
    
    df['expiry_date'] = pd.to_datetime(df['expiry_date'], errors='coerce')
    
    engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    df.to_sql('available_inventory_report', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"✓ Loaded {len(df)} rows into available_inventory_report")


def load_enrollment_rate_report():
    """Load enrollment rate report"""
    file_path = DATA_DIR / "enrollment_rate_report.csv"
    if not file_path.exists():
        print(f"⚠️  {file_path.name} not found")
        return
    
    df = pd.read_csv(file_path)
    df.columns = ['trial_alias', 'country', 'site', 'year', 'months_data']
    
    engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    df.to_sql('enrollment_rate_report', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"✓ Loaded {len(df)} rows into enrollment_rate_report")


def load_country_level_enrollment():
    """Load country level enrollment"""
    file_path = DATA_DIR / "country_level_enrollment_report.csv"
    if not file_path.exists():
        print(f"⚠️  {file_path.name} not found")
        return
    
    df = pd.read_csv(file_path)
    
    engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    df.to_sql('country_level_enrollment_report', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"✓ Loaded {len(df)} rows into country_level_enrollment_report")


def load_re_evaluation():
    """Load re-evaluation data"""
    file_path = DATA_DIR / "re-evaluation.csv"
    if not file_path.exists():
        print(f"⚠️  {file_path.name} not found")
        return
    
    df = pd.read_csv(file_path)
    
    # Rename columns
    df.columns = [
        're_eval_id', 'created_date', 'request_type', 'sample_status',
        'ly_number', 'item_code', 'lot_number', 'target_date',
        'sample_location', 'analytical_lab', 'analytical_rep_notified', 'modified_date'
    ]
    
    df['created_date'] = pd.to_datetime(df['created_date'], errors='coerce')
    df['target_date'] = pd.to_datetime(df['target_date'], errors='coerce')
    df['modified_date'] = pd.to_datetime(df['modified_date'], errors='coerce')
    
    engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    df.to_sql('re_evaluation', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"✓ Loaded {len(df)} rows into re_evaluation")


def load_rim():
    """Load RIM (Regulatory Information Management)"""
    file_path = DATA_DIR / "rim.csv"
    if not file_path.exists():
        print(f"⚠️  {file_path.name} not found")
        return
    
    df = pd.read_csv(file_path)
    
    df['approved_date_c'] = pd.to_datetime(df['approved_date_c'], errors='coerce')
    df['lilly_receipt_date_c'] = pd.to_datetime(df['lilly_receipt_date_c'], errors='coerce')
    
    engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    df.to_sql('rim', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"✓ Loaded {len(df)} rows into rim")


def load_material_country_requirements():
    """Load material country requirements"""
    file_path = DATA_DIR / "material_country_requirements.csv"
    if not file_path.exists():
        print(f"⚠️  {file_path.name} not found")
        return
    
    df = pd.read_csv(file_path)
    
    # Rename columns to match schema
    df.columns = [
        'client', 'countries', 'created_on', 'ct_compound', 'ct_label_group',
        'ct_pack_type', 'ct_pcn_group', 'date_of_last_change', 'material_number',
        'name_of_person_who_changed', 'time_of_creation', 'trial_alias'
    ]
    
    df['created_on'] = pd.to_datetime(df['created_on'], errors='coerce')
    df['date_of_last_change'] = pd.to_datetime(df['date_of_last_change'], errors='coerce')
    
    engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    df.to_sql('material_country_requirements', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"✓ Loaded {len(df)} rows into material_country_requirements")


def load_ip_shipping_timelines():
    """Load IP shipping timelines"""
    file_path = DATA_DIR / "ip_shipping_timelines_report.csv"
    if not file_path.exists():
        print(f"⚠️  {file_path.name} not found")
        return
    
    df = pd.read_csv(file_path)
    
    # Extract lead time in days
    df['lead_time_days'] = df['ip_timeline'].apply(parse_timeline)
    
    engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    df.to_sql('ip_shipping_timelines_report', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"✓ Loaded {len(df)} rows into ip_shipping_timelines_report")


def load_distribution_orders():
    """Load distribution orders"""
    file_path = DATA_DIR / "distribution_order_report.csv"
    if not file_path.exists():
        print(f"⚠️  {file_path.name} not found")
        return
    
    df = pd.read_csv(file_path)
    
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    df['requested_delivery_date'] = pd.to_datetime(df['requested_delivery_date'], errors='coerce')
    df['actual_delivery_date'] = pd.to_datetime(df['actual_delivery_date'], errors='coerce')
    
    engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    df.to_sql('distribution_order_report', engine, if_exists='replace', index=False, chunksize=1000)
    print(f"✓ Loaded {len(df)} rows into distribution_order_report")


def main():
    """Load all data files"""
    print("=" * 60)
    print("Clinical Supply Chain AI - Data Loading")
    print("=" * 60)
    print(f"\nData directory: {DATA_DIR}")
    print()
    
    # Load all tables
    loaders = [
        ("Allocated Materials", load_allocated_materials_to_orders),
        ("Available Inventory", load_available_inventory),
        ("Enrollment Rate", load_enrollment_rate_report),
        ("Country Enrollment", load_country_level_enrollment),
        ("Re-Evaluation", load_re_evaluation),
        ("RIM", load_rim),
        ("Material Requirements", load_material_country_requirements),
        ("Shipping Timelines", load_ip_shipping_timelines),
        ("Distribution Orders", load_distribution_orders),
    ]
    
    success = 0
    failed = 0
    
    for name, loader_func in loaders:
        try:
            print(f"\nLoading {name}...")
            loader_func()
            success += 1
        except Exception as e:
            print(f"✗ Error loading {name}: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"✓ Successfully loaded: {success} tables")
    if failed > 0:
        print(f"✗ Failed: {failed} tables")
    print("=" * 60)


if __name__ == "__main__":
    main()
