"""
Updated Database Schema based on Actual CSV Data
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "clinical_supply_chain")


def create_tables_for_actual_data():
    """Create tables matching the actual CSV structure"""
    
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )
    cursor = conn.cursor()
    
    tables = {
        # Core inventory and allocation tables
        "allocated_materials_to_orders": """
            CREATE TABLE IF NOT EXISTS allocated_materials_to_orders (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(100),
                material_component VARCHAR(100),
                material_component_batch VARCHAR(100),
                order_quantity INTEGER,
                fing_batch VARCHAR(100),
                order_status VARCHAR(50),
                ly_number VARCHAR(100),
                mrp_controller VARCHAR(50),
                mrp_group_desc VARCHAR(100),
                fing_material VARCHAR(100),
                material_comp_description TEXT,
                material_comp_type VARCHAR(100),
                material_description TEXT,
                modified_date TIMESTAMP,
                operation_number VARCHAR(50),
                operational_sequence_id VARCHAR(50),
                pcn_id VARCHAR(100),
                package_form VARCHAR(100),
                planned_or_process VARCHAR(100),
                plant VARCHAR(50),
                plant_desc VARCHAR(200),
                purchase_doc_number VARCHAR(100),
                recipe_id VARCHAR(50),
                supply_type VARCHAR(100),
                shared_across VARCHAR(100),
                trial VARCHAR(100),
                trial_alias VARCHAR(100),
                trial_alias_description TEXT,
                vendor_id VARCHAR(100),
                teco_flag VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_alloc_order_id ON allocated_materials_to_orders(order_id);
            CREATE INDEX IF NOT EXISTS idx_alloc_trial ON allocated_materials_to_orders(trial_alias);
            CREATE INDEX IF NOT EXISTS idx_alloc_batch ON allocated_materials_to_orders(material_component_batch);
        """,
        
        "available_inventory_report": """
            CREATE TABLE IF NOT EXISTS available_inventory_report (
                id SERIAL PRIMARY KEY,
                trial_name VARCHAR(200),
                location VARCHAR(200),
                investigator VARCHAR(200),
                package_type_description TEXT,
                lot VARCHAR(100),
                expiry_date DATE,
                packages_awaiting INTEGER,
                received_packages INTEGER,
                packages_pending_ffu INTEGER,
                packages_pending_shipment INTEGER,
                shipped_packages INTEGER,
                min_qty INTEGER,
                max_qty INTEGER,
                initial_qty INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_inv_trial ON available_inventory_report(trial_name);
            CREATE INDEX IF NOT EXISTS idx_inv_lot ON available_inventory_report(lot);
            CREATE INDEX IF NOT EXISTS idx_inv_expiry ON available_inventory_report(expiry_date);
            CREATE INDEX IF NOT EXISTS idx_inv_location ON available_inventory_report(location);
        """,
        
        "enrollment_rate_report": """
            CREATE TABLE IF NOT EXISTS enrollment_rate_report (
                id SERIAL PRIMARY KEY,
                trial_alias VARCHAR(100),
                country VARCHAR(200),
                site VARCHAR(100),
                year INTEGER,
                months_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_enroll_trial ON enrollment_rate_report(trial_alias);
            CREATE INDEX IF NOT EXISTS idx_enroll_country ON enrollment_rate_report(country);
        """,
        
        "country_level_enrollment_report": """
            CREATE TABLE IF NOT EXISTS country_level_enrollment_report (
                id SERIAL PRIMARY KEY,
                trial_alias VARCHAR(100),
                country_name VARCHAR(200),
                enrollment_level VARCHAR(50),
                total_enrolled_forecast INTEGER,
                total_enrolled_planned INTEGER,
                total_enrolled_actual INTEGER,
                enrollment_rate_monthly_actual DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_country_enroll_trial ON country_level_enrollment_report(trial_alias);
            CREATE INDEX IF NOT EXISTS idx_country_enroll_country ON country_level_enrollment_report(country_name);
        """,
        
        "re_evaluation": """
            CREATE TABLE IF NOT EXISTS re_evaluation (
                id SERIAL PRIMARY KEY,
                re_eval_id VARCHAR(100) UNIQUE,
                created_date DATE,
                request_type VARCHAR(100),
                sample_status VARCHAR(50),
                ly_number VARCHAR(100),
                item_code VARCHAR(100),
                lot_number VARCHAR(100),
                target_date DATE,
                sample_location VARCHAR(200),
                analytical_lab VARCHAR(200),
                analytical_rep_notified VARCHAR(200),
                modified_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_reeval_lot ON re_evaluation(lot_number);
            CREATE INDEX IF NOT EXISTS idx_reeval_ly ON re_evaluation(ly_number);
        """,
        
        "rim": """
            CREATE TABLE IF NOT EXISTS rim (
                id SERIAL PRIMARY KEY,
                name_v VARCHAR(300),
                filename_v VARCHAR(300),
                health_authority_division_c VARCHAR(100),
                type_v VARCHAR(100),
                status_v VARCHAR(50),
                approved_date_c DATE,
                major_version_number_v INTEGER,
                approver_v VARCHAR(200),
                lilly_receipt_date_c DATE,
                clinical_study_v VARCHAR(100),
                ly_number_c VARCHAR(100),
                submission_outcome VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_rim_study ON rim(clinical_study_v);
            CREATE INDEX IF NOT EXISTS idx_rim_ly ON rim(ly_number_c);
            CREATE INDEX IF NOT EXISTS idx_rim_status ON rim(status_v);
        """,
        
        "material_country_requirements": """
            CREATE TABLE IF NOT EXISTS material_country_requirements (
                id SERIAL PRIMARY KEY,
                client TEXT,
                countries VARCHAR(200),
                created_on DATE,
                ct_compound VARCHAR(200),
                ct_label_group VARCHAR(100),
                ct_pack_type VARCHAR(100),
                ct_pcn_group VARCHAR(100),
                date_of_last_change DATE,
                material_number VARCHAR(100),
                name_of_person_who_changed VARCHAR(200),
                time_of_creation TIME,
                trial_alias VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_mat_req_country ON material_country_requirements(countries);
            CREATE INDEX IF NOT EXISTS idx_mat_req_material ON material_country_requirements(material_number);
            CREATE INDEX IF NOT EXISTS idx_mat_req_trial ON material_country_requirements(trial_alias);
        """,
        
        "ip_shipping_timelines_report": """
            CREATE TABLE IF NOT EXISTS ip_shipping_timelines_report (
                id SERIAL PRIMARY KEY,
                ip_helper VARCHAR(300),
                ip_timeline VARCHAR(100),
                country_name VARCHAR(200),
                lead_time_days INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_ship_country ON ip_shipping_timelines_report(country_name);
        """,
        
        "distribution_order_report": """
            CREATE TABLE IF NOT EXISTS distribution_order_report (
                id SERIAL PRIMARY KEY,
                trial_alias VARCHAR(100),
                site_id VARCHAR(100),
                order_number VARCHAR(100) UNIQUE,
                ivrs_number VARCHAR(100),
                status VARCHAR(50),
                order_date DATE,
                requested_delivery_date DATE,
                actual_delivery_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_dist_trial ON distribution_order_report(trial_alias);
            CREATE INDEX IF NOT EXISTS idx_dist_order ON distribution_order_report(order_number);
            CREATE INDEX IF NOT EXISTS idx_dist_status ON distribution_order_report(status);
        """,
        
        "affiliate_warehouse_inventory": """
            CREATE TABLE IF NOT EXISTS affiliate_warehouse_inventory (
                id SERIAL PRIMARY KEY,
                warehouse_name VARCHAR(200),
                country VARCHAR(200),
                material_id VARCHAR(100),
                lot_number VARCHAR(100),
                quantity_on_hand INTEGER,
                expiry_date DATE,
                storage_condition VARCHAR(100),
                last_inventory_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_warehouse_country ON affiliate_warehouse_inventory(country);
            CREATE INDEX IF NOT EXISTS idx_warehouse_material ON affiliate_warehouse_inventory(material_id);
        """,
        
        "qdocs": """
            CREATE TABLE IF NOT EXISTS qdocs (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(100),
                document_type VARCHAR(100),
                material_id VARCHAR(100),
                batch_id VARCHAR(100),
                document_title TEXT,
                issue_date DATE,
                expiry_date DATE,
                document_status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_qdocs_material ON qdocs(material_id);
        """
    }
    
    for table_name, create_sql in tables.items():
        try:
            cursor.execute(create_sql)
            print(f"✓ Table '{table_name}' ready")
        except Exception as e:
            print(f"✗ Error with table '{table_name}': {e}")
    
    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    print("Creating tables for actual CSV data...")
    create_tables_for_actual_data()
    print("\n✓ All tables created successfully!")
