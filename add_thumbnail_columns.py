#!/usr/bin/env python3

import os
import psycopg2
from psycopg2 import sql

# Database connection
DATABASE_URL = "postgresql://postgres:History1014!@goodwave.cccmpneqxe0q.ap-northeast-2.rds.amazonaws.com:5432/goodwave_report"

def add_thumbnail_columns():
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'campaign_reel_collection_jobs' 
            AND column_name IN ('thumbnail_url', 's3_thumbnail_url');
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"Existing thumbnail columns: {existing_columns}")
        
        # Add thumbnail_url column if not exists
        if 'thumbnail_url' not in existing_columns:
            cursor.execute("ALTER TABLE campaign_reel_collection_jobs ADD COLUMN thumbnail_url TEXT;")
            print("✅ Added thumbnail_url column")
        else:
            print("📋 thumbnail_url column already exists")
            
        # Add s3_thumbnail_url column if not exists  
        if 's3_thumbnail_url' not in existing_columns:
            cursor.execute("ALTER TABLE campaign_reel_collection_jobs ADD COLUMN s3_thumbnail_url TEXT;")
            print("✅ Added s3_thumbnail_url column")
        else:
            print("📋 s3_thumbnail_url column already exists")
        
        # Commit the changes
        conn.commit()
        print("✅ Database migration completed successfully")
        
    except Exception as e:
        print(f"❌ Error adding thumbnail columns: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    add_thumbnail_columns()