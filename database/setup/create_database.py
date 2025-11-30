"""
PostgreSQL Database Setup Script for Clinical Supply Chain AI

This script creates all necessary tables for the supply chain control tower.
It assumes the CSV data files are provided by the client.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "clinical_supply_chain")


def create_database():
    """Create the main database if it doesn't exist."""
    print(f"Creating database '{DB_NAME}'...")
    
    # Connect to PostgreSQL server
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute(
        "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,)
    )
    exists = cursor.fetchone()
    
    if not exists:
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"✓ Database '{DB_NAME}' created successfully")
    else:
        print(f"✓ Database '{DB_NAME}' already exists")
    
    cursor.close()
    conn.close()


def create_tables():
    """Create all necessary tables based on the expected CSV structure."""
    print("\nCreating tables...")
    
    # Connect to the specific database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )
    cursor = conn.cursor()
    
    # Table creation SQL statements
    tables = {
        "allocated_materials": """
            CREATE TABLE IF NOT EXISTS allocated_materials (
                id SERIAL PRIMARY KEY,
                batch_id VARCHAR(100) NOT NULL,
                material_id VARCHAR(100) NOT NULL,
                material_description TEXT,
                trial_id VARCHAR(100),
                country_code VARCHAR(10),
                site_id VARCHAR(100),
                warehouse_id VARCHAR(50),
                allocated_quantity INTEGER,
                unit_of_measure VARCHAR(20),
                allocation_date DATE,
                expiry_date DATE,
                status VARCHAR(50),
                reserved_for VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_batch_id (batch_id),
                INDEX idx_material_id (material_id),
                INDEX idx_trial_country (trial_id, country_code),
                INDEX idx_expiry_date (expiry_date)
            );
        """,
        
        "available_inventory_report": """
            CREATE TABLE IF NOT EXISTS available_inventory_report (
                id SERIAL PRIMARY KEY,
                material_id VARCHAR(100) NOT NULL,
                material_description TEXT,
                warehouse_id VARCHAR(50),
                storage_location VARCHAR(100),
                available_quantity INTEGER,
                reserved_quantity INTEGER,
                unit_of_measure VARCHAR(20),
                batch_id VARCHAR(100),
                expiry_date DATE,
                last_updated TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_material_warehouse (material_id, warehouse_id),
                INDEX idx_batch_id (batch_id)
            );
        """,
        
        "enrollment_rate_report": """
            CREATE TABLE IF NOT EXISTS enrollment_rate_report (
                id SERIAL PRIMARY KEY,
                trial_id VARCHAR(100) NOT NULL,
                country_code VARCHAR(10),
                site_id VARCHAR(100),
                enrollment_date DATE NOT NULL,
                week_number INTEGER,
                patients_enrolled INTEGER,
                cumulative_enrollment INTEGER,
                target_enrollment INTEGER,
                enrollment_rate_pct DECIMAL(5,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_trial_country (trial_id, country_code),
                INDEX idx_enrollment_date (enrollment_date)
            );
        """,
        
        "country_level_enrollment": """
            CREATE TABLE IF NOT EXISTS country_level_enrollment (
                id SERIAL PRIMARY KEY,
                trial_id VARCHAR(100) NOT NULL,
                country_code VARCHAR(10) NOT NULL,
                country_name VARCHAR(100),
                projected_enrollment INTEGER,
                actual_enrollment INTEGER,
                enrollment_status VARCHAR(50),
                projection_date DATE,
                last_updated DATE,
                variance_pct DECIMAL(5,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_trial_country (trial_id, country_code),
                INDEX idx_projection_date (projection_date)
            );
        """,
        
        "affiliate_warehouse_inventory": """
            CREATE TABLE IF NOT EXISTS affiliate_warehouse_inventory (
                id SERIAL PRIMARY KEY,
                warehouse_id VARCHAR(50) NOT NULL,
                warehouse_name VARCHAR(200),
                country_code VARCHAR(10),
                material_id VARCHAR(100),
                batch_id VARCHAR(100),
                wh_lpn_number VARCHAR(100),
                quantity_on_hand INTEGER,
                quantity_allocated INTEGER,
                quantity_available INTEGER,
                expiry_date DATE,
                storage_condition VARCHAR(50),
                last_inventory_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_warehouse_material (warehouse_id, material_id),
                INDEX idx_lpn (wh_lpn_number)
            );
        """,
        
        "re_evaluation": """
            CREATE TABLE IF NOT EXISTS re_evaluation (
                id SERIAL PRIMARY KEY,
                batch_id VARCHAR(100) NOT NULL,
                material_id VARCHAR(100) NOT NULL,
                reeval_date DATE NOT NULL,
                reeval_type VARCHAR(50),
                outcome VARCHAR(50),
                original_expiry_date DATE,
                extended_expiry_date DATE,
                months_extended INTEGER,
                reason TEXT,
                approved_by VARCHAR(100),
                regulatory_reference VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_batch_id (batch_id),
                INDEX idx_reeval_date (reeval_date)
            );
        """,
        
        "rim": """
            CREATE TABLE IF NOT EXISTS rim (
                id SERIAL PRIMARY KEY,
                material_id VARCHAR(100) NOT NULL,
                country_code VARCHAR(10) NOT NULL,
                submission_type VARCHAR(100),
                submission_id VARCHAR(100),
                submission_date DATE,
                approval_status VARCHAR(50),
                approval_date DATE,
                regulatory_body VARCHAR(200),
                reference_number VARCHAR(100),
                expiry_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_material_country (material_id, country_code),
                INDEX idx_submission_type (submission_type)
            );
        """,
        
        "material_country_requirements": """
            CREATE TABLE IF NOT EXISTS material_country_requirements (
                id SERIAL PRIMARY KEY,
                material_id VARCHAR(100) NOT NULL,
                country_code VARCHAR(10) NOT NULL,
                country_name VARCHAR(100),
                shelf_life_extension_allowed BOOLEAN DEFAULT false,
                requires_submission BOOLEAN DEFAULT true,
                approval_lead_time_days INTEGER,
                max_extensions_allowed INTEGER,
                temperature_requirement VARCHAR(50),
                import_license_required BOOLEAN,
                special_requirements TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_material_country (material_id, country_code),
                UNIQUE (material_id, country_code)
            );
        """,
        
        "ip_shipping_timelines": """
            CREATE TABLE IF NOT EXISTS ip_shipping_timelines (
                id SERIAL PRIMARY KEY,
                origin_country VARCHAR(10),
                origin_warehouse VARCHAR(100),
                destination_country VARCHAR(10),
                destination_site VARCHAR(100),
                transport_mode VARCHAR(50),
                lead_time_days INTEGER,
                reliability_score DECIMAL(3,2),
                customs_clearance_days INTEGER,
                last_updated DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_origin_destination (origin_country, destination_country)
            );
        """,
        
        "distribution_order_report": """
            CREATE TABLE IF NOT EXISTS distribution_order_report (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(100) NOT NULL,
                order_date DATE,
                trial_id VARCHAR(100),
                material_id VARCHAR(100),
                batch_id VARCHAR(100),
                quantity_ordered INTEGER,
                quantity_shipped INTEGER,
                origin_warehouse VARCHAR(50),
                destination_country VARCHAR(10),
                destination_site VARCHAR(100),
                order_status VARCHAR(50),
                shipment_date DATE,
                expected_delivery_date DATE,
                actual_delivery_date DATE,
                tracking_number VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_order_id (order_id),
                INDEX idx_trial_id (trial_id),
                INDEX idx_order_status (order_status)
            );
        """,
        
        "qdocs": """
            CREATE TABLE IF NOT EXISTS qdocs (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(100) NOT NULL,
                document_type VARCHAR(100),
                material_id VARCHAR(100),
                batch_id VARCHAR(100),
                document_title TEXT,
                issue_date DATE,
                expiry_date DATE,
                document_status VARCHAR(50),
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_material_batch (material_id, batch_id),
                INDEX idx_document_type (document_type)
            );
        """,
        
        "trials_metadata": """
            CREATE TABLE IF NOT EXISTS trials_metadata (
                id SERIAL PRIMARY KEY,
                trial_id VARCHAR(100) UNIQUE NOT NULL,
                trial_name VARCHAR(300),
                indication VARCHAR(200),
                phase VARCHAR(20),
                sponsor VARCHAR(200),
                start_date DATE,
                expected_end_date DATE,
                status VARCHAR(50),
                target_enrollment INTEGER,
                number_of_countries INTEGER,
                number_of_sites INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_trial_id (trial_id),
                INDEX idx_indication (indication)
            );
        """
    }
    
    for table_name, create_sql in tables.items():
        try:
            cursor.execute(create_sql)
            print(f"✓ Table '{table_name}' created successfully")
        except Exception as e:
            print(f"✗ Error creating table '{table_name}': {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("\nAll tables created successfully!")


def create_views():
    """Create useful views for common queries."""
    print("\nCreating views...")
    
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )
    cursor = conn.cursor()
    
    views = {
        "v_expiring_inventory": """
            CREATE OR REPLACE VIEW v_expiring_inventory AS
            SELECT 
                am.trial_id,
                am.country_code,
                am.material_id,
                am.batch_id,
                am.expiry_date,
                EXTRACT(DAY FROM (am.expiry_date - CURRENT_DATE)) as days_until_expiry,
                am.allocated_quantity,
                CASE 
                    WHEN EXTRACT(DAY FROM (am.expiry_date - CURRENT_DATE)) <= 30 THEN 'CRITICAL'
                    WHEN EXTRACT(DAY FROM (am.expiry_date - CURRENT_DATE)) <= 60 THEN 'HIGH'
                    WHEN EXTRACT(DAY FROM (am.expiry_date - CURRENT_DATE)) <= 90 THEN 'MEDIUM'
                    ELSE 'LOW'
                END as risk_level
            FROM allocated_materials am
            WHERE am.expiry_date >= CURRENT_DATE
            AND am.expiry_date <= CURRENT_DATE + INTERVAL '90 days'
            ORDER BY am.expiry_date ASC;
        """,
        
        "v_inventory_summary": """
            CREATE OR REPLACE VIEW v_inventory_summary AS
            SELECT 
                air.material_id,
                air.warehouse_id,
                SUM(air.available_quantity) as total_available,
                SUM(air.reserved_quantity) as total_reserved,
                COUNT(DISTINCT air.batch_id) as number_of_batches,
                MIN(air.expiry_date) as earliest_expiry,
                MAX(air.last_updated) as last_updated
            FROM available_inventory_report air
            WHERE air.expiry_date > CURRENT_DATE
            GROUP BY air.material_id, air.warehouse_id;
        """,
        
        "v_enrollment_trends": """
            CREATE OR REPLACE VIEW v_enrollment_trends AS
            SELECT 
                err.trial_id,
                err.country_code,
                DATE_TRUNC('week', err.enrollment_date) as week_start,
                SUM(err.patients_enrolled) as weekly_enrollment,
                AVG(err.patients_enrolled) OVER (
                    PARTITION BY err.trial_id, err.country_code 
                    ORDER BY err.enrollment_date 
                    ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
                ) as moving_avg_4weeks
            FROM enrollment_rate_report err
            WHERE err.enrollment_date >= CURRENT_DATE - INTERVAL '12 weeks'
            GROUP BY err.trial_id, err.country_code, DATE_TRUNC('week', err.enrollment_date), err.enrollment_date, err.patients_enrolled
            ORDER BY err.trial_id, err.country_code, week_start;
        """
    }
    
    for view_name, create_sql in views.items():
        try:
            cursor.execute(create_sql)
            print(f"✓ View '{view_name}' created successfully")
        except Exception as e:
            print(f"✗ Error creating view '{view_name}': {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("\nAll views created successfully!")


if __name__ == "__main__":
    print("=" * 60)
    print("Clinical Supply Chain AI - Database Setup")
    print("=" * 60)
    
    try:
        create_database()
        create_tables()
        create_views()
        
        print("\n" + "=" * 60)
        print("✓ Database setup completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Place your CSV files in the database/data/ directory")
        print("2. Run: python database/setup/load_data.py")
        print("3. Verify data: python database/setup/verify_data.py")
        
    except Exception as e:
        print(f"\n✗ Error during database setup: {e}")
        raise
