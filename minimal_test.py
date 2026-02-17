#!/usr/bin/env python3
"""
Minimal test to check database connectivity without heavy dependencies
"""

import asyncio
import os

async def test_database_connection():
    """Test basic database connectivity"""
    print("🧪 Database Connectivity Test")
    print("=" * 40)

    try:
        import asyncpg

        # Try to connect to database
        database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/knowledge_aligner')
        print(f"Connecting to: {database_url.split('@')[-1] if '@' in database_url else database_url}")

        conn = await asyncpg.connect(database_url)
        print("✅ Database connection successful")

        # Check if basic tables exist
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public' AND tablename IN ('user_profiles', 'decisions', 'slack_messages')
            ORDER BY tablename
        """)

        print(f"Found {len(tables)} core tables:")
        for table in tables:
            print(f"  - {table['tablename']}")

        if len(tables) >= 3:
            # Check sample data
            user_count = await conn.fetchval("SELECT COUNT(*) FROM user_profiles")
            decision_count = await conn.fetchval("SELECT COUNT(*) FROM decisions")
            print(f"\nData summary:")
            print(f"  - Users: {user_count}")
            print(f"  - Decisions: {decision_count}")

        await conn.close()

        if len(tables) >= 3:
            print("\n🎉 Database is properly initialized and has data!")
            return True
        else:
            print("\n⚠️  Database connected but missing tables. Need to run initialization.")
            return False

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def check_environment():
    """Check required environment variables"""
    print("\n🔑 Environment Check")
    print("-" * 40)

    env_vars = {
        'DATABASE_URL': os.getenv('DATABASE_URL'),
        'ANTHROPIC_API_KEY': '✅ Set' if os.getenv('ANTHROPIC_API_KEY') else '❌ Missing',
        'OPENAI_API_KEY': '✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'
    }

    for var, value in env_vars.items():
        if var == 'DATABASE_URL':
            display_value = value.split('@')[-1] if value and '@' in value else (value or 'Using default')
            print(f"  {var}: {display_value}")
        else:
            print(f"  {var}: {value}")

async def main():
    """Run minimal connectivity test"""
    print("🚀 Knowledge Aligner - Minimal Connectivity Test")
    print("=" * 60)

    await check_environment()

    db_ok = await test_database_connection()

    if db_ok:
        print("\n✅ System ready for full testing!")
        print("\nNext steps:")
        print("  1. Install ML dependencies: pip install sentence-transformers numpy scikit-learn")
        print("  2. Run full test: python test_production.py")
        return 0
    else:
        print("\n🔧 Database needs initialization:")
        print("  1. Start PostgreSQL with pgvector extension")
        print("  2. Run: cd backend && python cli.py db init")
        print("  3. Then run this test again")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())