#!/usr/bin/env python3
"""
Production System Test
Quick verification that all components work together
"""

import asyncio
import os
import sys
import time
from datetime import datetime

# Add backend to path
sys.path.append('./backend')

from database_manager import db_manager
from hybrid_retrieval import HybridRetrieval
from embedding_pipeline import EmbeddingPipeline

async def test_production_system():
    """Test the complete production system"""
    print("🧪 Testing Knowledge Aligner Production System")
    print("=" * 60)

    test_results = []
    start_time = time.time()

    try:
        # 1. Database Connection Test
        print("\n1️⃣  Testing Database Connection...")
        await db_manager.init_pool()
        status = await db_manager.get_system_status()
        print(f"   ✅ Connected to database")
        print(f"   📊 Found {status['decisions']} decisions, {status['users']} users")
        test_results.append(("Database Connection", True))

        # 2. User Management Test
        print("\n2️⃣  Testing User Management...")
        alice = await db_manager.get_user("alice")
        if alice:
            print(f"   ✅ Retrieved user: {alice['user_name']} ({alice['role']})")
            print(f"   🔧 Components: {alice['owned_components']}")
            test_results.append(("User Management", True))
        else:
            print("   ❌ Failed to retrieve user")
            test_results.append(("User Management", False))

        # 3. Decision Retrieval Test
        print("\n3️⃣  Testing Decision Retrieval...")
        decisions = await db_manager.get_decisions(user_id="alice", limit=5)
        print(f"   ✅ Retrieved {len(decisions)} decisions for Alice")
        if decisions:
            decision = decisions[0]
            print(f"   📋 Latest: REQ-{decision['decision_id']:03d} by {decision['author_name']}")
            print(f"   🔧 Components: {decision['affected_components']}")
        test_results.append(("Decision Retrieval", len(decisions) > 0))

        # 4. Gap Detection Test
        print("\n4️⃣  Testing Gap Detection...")
        gaps = await db_manager.get_gaps("alice")
        print(f"   ✅ Found {len(gaps)} gaps for Alice")
        if gaps:
            gap = gaps[0]
            print(f"   ⚠️  Top priority: P{gap['priority']} - {gap['type']}")
            print(f"   📝 Description: {gap['description'][:60]}...")
        test_results.append(("Gap Detection", len(gaps) > 0))

        # 5. Hybrid Retrieval Test
        print("\n5️⃣  Testing Hybrid Retrieval...")
        retriever = HybridRetrieval()
        await retriever.init_db_pool(db_manager.database_url)

        search_start = time.time()
        results, stats = await retriever.hybrid_search(
            user_id="alice",
            query_text="motor torque",
            limit=3
        )
        search_time = (time.time() - search_start) * 1000

        print(f"   ✅ Search completed in {search_time:.1f}ms")
        print(f"   🔍 Query type: {stats.query_type}")
        print(f"   📊 Found {len(results)} results from {stats.candidates_found} candidates")

        if results:
            result = results[0]
            print(f"   🎯 Top result: [{result.decision_id}] {result.author_name}")
            print(f"   📈 Similarity: {result.similarity_score:.3f}")

        performance_good = stats.total_time_ms < 100  # Target <40ms, accept <100ms for test
        test_results.append(("Hybrid Retrieval", performance_good))
        test_results.append(("Performance Target", stats.total_time_ms < 40))

        await retriever.close()

        # 6. Priority Management Test
        print("\n6️⃣  Testing Priority Management...")
        if gaps:
            gap_id = gaps[0]['decision_id']
            success = await db_manager.update_gap_priority(gap_id, 1)
            if success:
                print(f"   ✅ Updated gap {gap_id} priority to 1")
                test_results.append(("Priority Management", True))
            else:
                print(f"   ❌ Failed to update gap priority")
                test_results.append(("Priority Management", False))
        else:
            print("   ⚠️  No gaps to test priority management")
            test_results.append(("Priority Management", None))

        # 7. Chat Context Test
        print("\n7️⃣  Testing Chat Context...")
        context = await db_manager.get_chat_context("alice", "What are my priorities?")
        if "error" not in context:
            user = context["user"]
            decisions = context["recent_decisions"]
            gaps = context["priority_gaps"]
            print(f"   ✅ Generated context for {user['user_name']}")
            print(f"   📋 {len(decisions)} relevant decisions")
            print(f"   ⚠️  {len(gaps)} priority gaps")
            test_results.append(("Chat Context", True))
        else:
            print(f"   ❌ Chat context failed: {context['error']}")
            test_results.append(("Chat Context", False))

        # 8. Embedding Status Test
        print("\n8️⃣  Testing Embedding Status...")
        pipeline = EmbeddingPipeline()
        await pipeline.init_db_pool()
        stats = await pipeline.get_embedding_stats()

        print(f"   📊 Embedding statistics:")
        print(f"      Total decisions: {stats['total_decisions']}")
        print(f"      Embedded: {stats['embedded']}")
        print(f"      Pending: {stats['pending']}")

        # Check if we have embeddings
        has_embeddings = stats['embedded'] > 0
        test_results.append(("Embeddings Available", has_embeddings))

        if stats['pending'] > 0:
            print(f"   ℹ️  Note: {stats['pending']} decisions need embedding")

        await pipeline.close()

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        test_results.append(("System Error", False))

    finally:
        await db_manager.close()

    # Results Summary
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    for test_name, result in test_results:
        if result is True:
            status = "✅ PASS"
            passed += 1
        elif result is False:
            status = "❌ FAIL"
            failed += 1
        else:
            status = "⚠️  SKIP"
            skipped += 1

        print(f"{test_name:<25} {status}")

    print("-" * 60)
    print(f"Total Tests: {len(test_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Duration: {total_time:.2f}s")

    # Overall Assessment
    if failed == 0:
        if passed >= 6:  # Most critical tests passed
            print("\n🎉 PRODUCTION SYSTEM READY!")
            print("   All critical components are functional")
            if skipped > 0:
                print(f"   Note: {skipped} tests skipped (non-critical)")
        else:
            print("\n⚠️  SYSTEM PARTIALLY FUNCTIONAL")
            print("   Some components may need setup")
    else:
        print("\n❌ SYSTEM NEEDS ATTENTION")
        print(f"   {failed} critical components failed")
        print("   Review error messages above")

    return failed == 0 and passed >= 6

async def main():
    """Main test execution"""
    # Check environment
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/knowledge_aligner')
    print(f"🔗 Database URL: {database_url.split('@')[-1] if '@' in database_url else database_url}")

    # Check API keys
    anthropic_key = bool(os.getenv('ANTHROPIC_API_KEY'))
    openai_key = bool(os.getenv('OPENAI_API_KEY'))
    print(f"🔑 Anthropic API: {'✅' if anthropic_key else '❌'}")
    print(f"🔑 OpenAI API: {'✅' if openai_key else '❌'}")

    success = await test_production_system()

    if success:
        print("\n🚀 System ready for EverCurrent demo!")
        return 0
    else:
        print("\n🔧 Please fix issues before demo")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())