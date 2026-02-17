#!/usr/bin/env python3
"""
Knowledge Aligner CLI Tools
Comprehensive command-line interface for testing and managing the production system
"""

import asyncio
import click
import json
import os
import time
from datetime import datetime
from typing import List, Dict

# Import our production modules
from database_manager import db_manager
from hybrid_retrieval import HybridRetrieval
from embedding_pipeline import EmbeddingPipeline
from entity_extraction import EntityExtractor

@click.group()
@click.option('--database-url', envvar='DATABASE_URL',
              default='postgresql://postgres:postgres@localhost:5432/knowledge_aligner',
              help='PostgreSQL database URL')
@click.pass_context
def cli(ctx, database_url):
    """Knowledge Aligner CLI - Production system management and testing"""
    ctx.ensure_object(dict)
    ctx.obj['database_url'] = database_url

@cli.group()
def db():
    """Database management commands"""
    pass

@db.command()
@click.pass_context
async def status(ctx):
    """Show database status and statistics"""
    try:
        await db_manager.init_pool()
        status = await db_manager.get_system_status()

        click.echo("📊 Database Status:")
        click.echo(f"  Users: {status['users']}")
        click.echo(f"  Decisions: {status['decisions']}")
        click.echo(f"  Messages: {status['messages']}")
        click.echo(f"  Relationships: {status['relationships']}")
        click.echo(f"  Database: {status['database_url']}")
        click.echo(f"  AI Enabled: {status['ai_enabled']}")

        embeddings = status['embeddings']
        click.echo(f"\n🔢 Embedding Status:")
        click.echo(f"  Embedded: {embeddings.get('embedded', 0)}")
        click.echo(f"  Pending: {embeddings.get('pending', 0)}")
        click.echo(f"  Failed: {embeddings.get('failed', 0)}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
    finally:
        await db_manager.close()

@db.command()
@click.pass_context
async def init(ctx):
    """Initialize database with schema and seed data"""
    import asyncpg

    try:
        # Connect to database
        conn = await asyncpg.connect(ctx.obj['database_url'])

        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql')
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        await conn.execute(schema_sql)
        click.echo("✅ Schema created")

        # Read and execute seed data
        seed_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'seed_data.sql')
        with open(seed_path, 'r') as f:
            seed_sql = f.read()

        await conn.execute(seed_sql)
        click.echo("✅ Seed data inserted")

        await conn.close()

    except Exception as e:
        click.echo(f"❌ Error: {e}")

@cli.group()
def embed():
    """Embedding pipeline commands"""
    pass

@embed.command()
@click.option('--batch-size', default=100, help='Batch size for processing')
@click.option('--max-batches', default=None, type=int, help='Maximum batches to process')
@click.pass_context
async def run(ctx, batch_size, max_batches):
    """Run batch embedding pipeline"""
    pipeline = EmbeddingPipeline()

    try:
        await pipeline.init_db_pool()

        click.echo(f"🚀 Starting embedding pipeline (batch_size={batch_size})")
        start_time = time.time()

        total_processed = await pipeline.batch_process(batch_size, max_batches)

        duration = time.time() - start_time
        click.echo(f"✅ Processed {total_processed} decisions in {duration:.2f}s")

        if total_processed > 0:
            click.echo(f"   Average: {duration/total_processed:.3f}s per decision")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
    finally:
        await pipeline.close()

@embed.command()
@click.pass_context
async def stats(ctx):
    """Show embedding statistics"""
    pipeline = EmbeddingPipeline()

    try:
        await pipeline.init_db_pool()
        stats = await pipeline.get_embedding_stats()

        click.echo("📊 Embedding Statistics:")
        click.echo(f"  Total decisions: {stats['total_decisions']}")
        click.echo(f"  Embedded: {stats['embedded']}")
        click.echo(f"  Pending: {stats['pending']}")
        click.echo(f"  Failed: {stats['failed']}")
        click.echo(f"  Stale: {stats['stale']}")
        click.echo(f"  Avg words per decision: {stats['avg_word_count']:.1f}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
    finally:
        await pipeline.close()

@cli.group()
def search():
    """Hybrid retrieval testing commands"""
    pass

@search.command()
@click.argument('query')
@click.option('--user-id', default='alice', help='User ID for component filtering')
@click.option('--limit', default=10, help='Number of results')
@click.pass_context
async def test(ctx, query, user_id, limit):
    """Test hybrid search with a query"""
    retriever = HybridRetrieval()

    try:
        await retriever.init_db_pool(ctx.obj['database_url'])

        click.echo(f"🔍 Searching: '{query}' (user: {user_id})")
        start_time = time.time()

        results, stats = await retriever.hybrid_search(
            user_id=user_id,
            query_text=query,
            limit=limit
        )

        duration = time.time() - start_time

        click.echo(f"\n⚡ Performance:")
        click.echo(f"  Total: {stats.total_time_ms:.1f}ms")
        click.echo(f"  SQL Filter: {stats.sql_filter_time_ms:.1f}ms")
        click.echo(f"  Semantic: {stats.semantic_search_time_ms:.1f}ms")
        click.echo(f"  Query Type: {stats.query_type}")
        click.echo(f"  Candidates: {stats.candidates_found}")

        click.echo(f"\n📋 Results ({len(results)}):")
        for i, result in enumerate(results[:5]):
            click.echo(f"  {i+1}. [{result.decision_id}] {result.author_name}")
            click.echo(f"     Similarity: {result.similarity_score:.3f}")
            click.echo(f"     Components: {result.affected_components}")
            click.echo(f"     Text: {result.decision_text[:80]}...")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error: {e}")
    finally:
        await retriever.close()

@search.command()
@click.option('--user-id', default='alice', help='User ID for testing')
@click.pass_context
async def benchmark(ctx, user_id):
    """Run comprehensive search benchmarks"""
    retriever = HybridRetrieval()

    try:
        await retriever.init_db_pool(ctx.obj['database_url'])

        test_queries = [
            "motor torque requirements",
            "power supply capacity",
            "firmware update security",
            "PCB design changes",
            "component selection criteria"
        ]

        click.echo(f"🏁 Running benchmark with {len(test_queries)} queries...")

        results = await retriever.benchmark_performance(test_queries, user_id)

        click.echo("\n📊 Performance Results:")
        for method, stats in results.items():
            click.echo(f"\n{method.upper()}:")
            click.echo(f"  Average: {stats['avg_time_ms']:.1f}ms")
            click.echo(f"  P50: {stats['p50_time_ms']:.1f}ms")
            click.echo(f"  P95: {stats['p95_time_ms']:.1f}ms")
            click.echo(f"  P99: {stats['p99_time_ms']:.1f}ms")
            click.echo(f"  Min: {stats['min_time_ms']:.1f}ms")
            click.echo(f"  Max: {stats['max_time_ms']:.1f}ms")

            # Performance assessment
            if stats['p95_time_ms'] < 40:
                click.echo(f"  Status: ✅ Excellent (<40ms target)")
            elif stats['p95_time_ms'] < 100:
                click.echo(f"  Status: ⚠️  Good but could improve")
            else:
                click.echo(f"  Status: ❌ Needs optimization")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
    finally:
        await retriever.close()

@cli.group()
def extract():
    """Entity extraction commands"""
    pass

@extract.command()
@click.argument('message')
@click.pass_context
async def test(ctx, message):
    """Test entity extraction on a message"""
    extractor = EntityExtractor()

    try:
        await extractor.init_claude_client()

        click.echo(f"🔍 Extracting entities from: '{message}'")

        entities = await extractor.extract_with_claude(message)

        click.echo("\n📋 Extracted Entities:")
        click.echo(f"  Requirements: {entities.requirements}")
        click.echo(f"  Components: {entities.components}")
        click.echo(f"  Decision Indicators: {entities.decision_indicators}")
        click.echo(f"  Before/After: {entities.before_after}")
        click.echo(f"  Decision Type: {entities.decision_type}")
        click.echo(f"  Confidence: {entities.confidence:.2f}")
        click.echo(f"  Mentions: {entities.mentions}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
    finally:
        await extractor.close()

@extract.command()
@click.option('--limit', default=100, help='Number of messages to process')
@click.pass_context
async def batch(ctx, limit):
    """Process unprocessed Slack messages"""
    extractor = EntityExtractor()

    try:
        await extractor.init_claude_client()
        await extractor.init_db_pool(ctx.obj['database_url'])

        click.echo(f"🚀 Processing up to {limit} messages...")

        decisions_created = await extractor.batch_process_messages(limit)

        click.echo(f"✅ Created {decisions_created} decisions from batch processing")

        # Show extraction stats
        stats = await extractor.get_extraction_stats()
        click.echo("\n📊 Extraction Statistics:")
        click.echo(json.dumps(stats, indent=2, default=str))

    except Exception as e:
        click.echo(f"❌ Error: {e}")
    finally:
        await extractor.close()

@cli.command()
@click.option('--query', help='Test query')
@click.option('--user-id', default='alice', help='User ID')
@click.pass_context
async def demo(ctx, query, user_id):
    """Run end-to-end demo of the system"""
    click.echo("🚀 Knowledge Aligner Demo")
    click.echo("=" * 50)

    try:
        # Initialize system
        await db_manager.init_pool()

        # 1. Show system status
        click.echo("\n1️⃣  System Status:")
        status = await db_manager.get_system_status()
        click.echo(f"   Decisions: {status['decisions']}")
        click.echo(f"   Users: {status['users']}")
        click.echo(f"   AI Enabled: {status['ai_enabled']}")

        # 2. Show user info
        click.echo(f"\n2️⃣  User Profile ({user_id}):")
        user = await db_manager.get_user(user_id)
        if user:
            click.echo(f"   Name: {user['user_name']}")
            click.echo(f"   Role: {user['role']}")
            click.echo(f"   Components: {user['owned_components']}")

        # 3. Show gaps
        click.echo(f"\n3️⃣  Priority Gaps for {user_id}:")
        gaps = await db_manager.get_gaps(user_id)
        for i, gap in enumerate(gaps[:3]):
            click.echo(f"   {i+1}. P{gap['priority']} - {gap['type']}")
            click.echo(f"      {gap['description'][:60]}...")

        # 4. Hybrid search demo
        if query:
            click.echo(f"\n4️⃣  Hybrid Search: '{query}'")
            retriever = HybridRetrieval()
            await retriever.init_db_pool(ctx.obj['database_url'])

            results, stats = await retriever.hybrid_search(user_id, query, limit=3)

            click.echo(f"   Performance: {stats.total_time_ms:.1f}ms ({stats.query_type})")
            for i, result in enumerate(results):
                click.echo(f"   {i+1}. [{result.decision_id}] {result.author_name} (sim: {result.similarity_score:.2f})")

            await retriever.close()

        # 5. Show recent decisions
        click.echo(f"\n5️⃣  Recent Decisions for {user_id}:")
        decisions = await db_manager.get_decisions(user_id, limit=3)
        for decision in decisions:
            click.echo(f"   REQ-{decision['decision_id']:03d}: {decision['author_name']}")
            click.echo(f"   Components: {decision['affected_components']}")
            click.echo(f"   {decision['decision_text'][:60]}...")
            click.echo()

        click.echo("✅ Demo complete!")

    except Exception as e:
        click.echo(f"❌ Demo failed: {e}")
    finally:
        await db_manager.close()

@cli.command()
@click.pass_context
async def validate(ctx):
    """Validate production system setup"""
    click.echo("🔍 Validating Knowledge Aligner Setup")
    click.echo("=" * 40)

    validation_results = []

    # 1. Database connection
    try:
        await db_manager.init_pool()
        status = await db_manager.get_system_status()
        validation_results.append(("Database Connection", "✅ Connected"))
        validation_results.append(("Decisions in DB", f"✅ {status['decisions']} records"))
        validation_results.append(("Users in DB", f"✅ {status['users']} records"))
    except Exception as e:
        validation_results.append(("Database Connection", f"❌ {e}"))

    # 2. Embedding pipeline
    try:
        pipeline = EmbeddingPipeline()
        await pipeline.init_model()
        validation_results.append(("Embedding Model", "✅ sentence-transformers loaded"))
        await pipeline.close()
    except Exception as e:
        validation_results.append(("Embedding Model", f"❌ {e}"))

    # 3. Entity extraction
    try:
        extractor = EntityExtractor()
        claude_available = await extractor.init_claude_client()
        if claude_available:
            validation_results.append(("Claude API", "✅ Available"))
        else:
            validation_results.append(("Claude API", "⚠️  No API key (fallback mode)"))
    except Exception as e:
        validation_results.append(("Claude API", f"❌ {e}"))

    # 4. OpenAI API
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        validation_results.append(("OpenAI API", "✅ API key configured"))
    else:
        validation_results.append(("OpenAI API", "⚠️  No API key"))

    # 5. Hybrid retrieval
    try:
        retriever = HybridRetrieval()
        await retriever.init_db_pool(ctx.obj['database_url'])
        results, stats = await retriever.hybrid_search("alice", "test", limit=1)
        validation_results.append(("Hybrid Retrieval", f"✅ {stats.total_time_ms:.1f}ms"))
        await retriever.close()
    except Exception as e:
        validation_results.append(("Hybrid Retrieval", f"❌ {e}"))

    # Print results
    click.echo()
    for component, result in validation_results:
        click.echo(f"{component:<20} {result}")

    # Overall assessment
    errors = sum(1 for _, result in validation_results if result.startswith("❌"))
    warnings = sum(1 for _, result in validation_results if result.startswith("⚠️"))

    click.echo()
    if errors == 0 and warnings == 0:
        click.echo("🎉 All systems operational! Ready for production.")
    elif errors == 0:
        click.echo(f"⚠️  System functional with {warnings} warnings.")
    else:
        click.echo(f"❌ {errors} critical issues need resolution.")

    await db_manager.close()

# Convert sync commands to async
def make_async_command(func):
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

# Apply async wrapper to all commands
for command in [status, init, run, stats, test, benchmark, batch, demo, validate]:
    command.callback = make_async_command(command.callback)

for command in [extract.commands['test'], extract.commands['batch']]:
    command.callback = make_async_command(command.callback)

if __name__ == '__main__':
    cli()