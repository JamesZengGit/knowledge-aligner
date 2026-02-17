#!/usr/bin/env python3
"""
Quick test to verify database connectivity and basic components
"""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_database():
    """Test database connectivity"""
    print("🧪 Quick Database Test")
    print("=" * 40)

    try:
        import asyncpg

        # Try to connect to database
        database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/knowledge_aligner')
        print(f"Database URL: {database_url.split('@')[-1] if '@' in database_url else database_url}")

        conn = await asyncpg.connect(database_url)

        # Check if tables exist
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)

        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table['tablename']}")

        # Check users
        if any(t['tablename'] == 'user_profiles' for t in tables):
            users = await conn.fetch("SELECT user_id, user_name, role FROM user_profiles")
            print(f"\nFound {len(users)} users:")
            for user in users:
                print(f"  - {user['user_name']} ({user['role']})")

        # Check decisions
        if any(t['tablename'] == 'decisions' for t in tables):
            decisions_count = await conn.fetchval("SELECT COUNT(*) FROM decisions")
            print(f"\nFound {decisions_count} decisions in database")

        await conn.close()

        print("\n✅ Database connectivity test PASSED")
        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

async def test_imports():
    """Test that our modules can be imported"""
    print("\n🔍 Testing Module Imports")
    print("-" * 40)

    modules_to_test = [
        ('database_manager', 'DatabaseManager'),
    ]

    results = []

    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name)
            if hasattr(module, class_name):
                print(f"✅ {module_name}.{class_name}")
                results.append(True)
            else:
                print(f"❌ {module_name} missing {class_name}")
                results.append(False)
        except Exception as e:
            print(f"❌ {module_name} import failed: {e}")
            results.append(False)

    return all(results)

async def main():
    """Run quick tests"""
    print("🚀 Knowledge Aligner Quick Test")
    print("=" * 50)

    # Test imports first
    imports_ok = await test_imports()

    # Test database if imports worked
    if imports_ok:
        db_ok = await test_database()

        if db_ok:
            print("\n🎉 Basic system components are working!")
            print("Ready to run full production test.")
            return 0
        else:
            print("\n🔧 Database needs setup. Run: python backend/cli.py db init")
            return 1
    else:
        print("\n🔧 Module import issues detected.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)