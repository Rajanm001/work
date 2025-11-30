"""
Basic database connection and query tests
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
import psycopg2
from agents.config import config


def test_database_connection():
    """Test that database connection works"""
    try:
        conn = psycopg2.connect(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            dbname=config.db_name
        )
        assert conn is not None
        conn.close()
    except Exception as e:
        pytest.fail(f"Database connection failed: {e}")


def test_inventory_table_exists():
    """Test that main inventory table exists and has data"""
    conn = psycopg2.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        dbname=config.db_name
    )
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM available_inventory_report;")
    result = cursor.fetchone()
    count = result[0] if result else 0
    
    assert count > 0, "Inventory table should have data"
    
    cursor.close()
    conn.close()


def test_expiring_inventory_query():
    """Test query for expiring inventory"""
    conn = psycopg2.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        dbname=config.db_name
    )
    cursor = conn.cursor()
    
    query = """
        SELECT COUNT(*) 
        FROM available_inventory_report
        WHERE expiry_date IS NOT NULL
        AND expiry_date::date > CURRENT_DATE
        AND expiry_date::date <= CURRENT_DATE + INTERVAL '90 days';
    """
    
    cursor.execute(query)
    result = cursor.fetchone()
    count = result[0] if result else 0
    
    assert count >= 0, "Query should execute successfully"
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
