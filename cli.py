"""CLI interface for the Slack digest system."""

import click
import asyncio
import time
import json
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from typing import Optional

# Import our modules
from src.database import init_db, get_db, refresh_materialized_view
from src.data_generator import HardwareTeamDataGenerator
from src.entity_extractor import EntityExtractor
from src.decision_graph import DecisionGraphBuilder
from src.embedding_pipeline import EmbeddingPipeline
from src.retrieval import HybridRetriever
from src.digest_generator import DigestGenerator
from src.gap_detector import GapDetector
from src.models import *

@click.group()
def cli():
    """Hardware Team Slack Digest CLI - EverCurrent Demo"""
    pass

@cli.command()
def setup():
    """Initialize database and load sample data."""
    click.echo("🚀 Setting up Slack digest database...")

    try:
        # Initialize database
        init_db()
        click.echo("✅ Database schema created")

        # Generate and load sample data
        generator = HardwareTeamDataGenerator()

        # Insert users
        with get_db() as db:
            cursor = db.cursor()

            # Insert user profiles
            for user in generator.users:
                cursor.execute("""
                    INSERT INTO user_profiles (user_id, user_name, role, owned_components, email)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (user.user_id, user.user_name, user.role, user.owned_components, user.email))

            click.echo(f"✅ Inserted {len(generator.users)} user profiles")

            # Generate and insert messages
            messages = generator.generate_realistic_conversations()

            for msg in messages:
                cursor.execute("""
                    INSERT INTO slack_messages (message_id, channel_id, thread_id, user_id, message_text, timestamp, entities)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO NOTHING
                """, (msg.message_id, msg.channel_id, msg.thread_id, msg.user_id,
                      msg.message_text, msg.timestamp, json.dumps(msg.entities)))

            click.echo(f"✅ Inserted {len(messages)} Slack messages")

        click.echo("🎉 Setup complete! Run 'python cli.py ingest' to process messages.")

    except Exception as e:
        click.echo(f"❌ Setup failed: {e}")
        raise

@cli.command()
@click.option('--batch-size', default=100, help='Number of messages to process at once')
def ingest(batch_size):
    """Extract entities from Slack messages and create decisions."""
    click.echo("🔍 Extracting entities and creating decisions...")

    try:
        extractor = EntityExtractor()
        graph_builder = DecisionGraphBuilder()

        with get_db() as db:
            cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Get unprocessed messages
            cursor.execute("""
                SELECT message_id, channel_id, thread_id, user_id, message_text, timestamp, entities
                FROM slack_messages
                WHERE message_id NOT IN (
                    SELECT DISTINCT sm.message_id
                    FROM slack_messages sm
                    JOIN decisions d ON sm.thread_id = d.thread_id
                )
                ORDER BY timestamp
                LIMIT %s
            """, (batch_size * 10,))  # Get more messages than batch size

            messages = [SlackMessage(
                message_id=row['message_id'],
                channel_id=row['channel_id'],
                thread_id=row['thread_id'],
                user_id=row['user_id'],
                message_text=row['message_text'],
                timestamp=row['timestamp'],
                entities=row['entities']
            ) for row in cursor.fetchall()]

            if not messages:
                click.echo("No new messages to process")
                return

            click.echo(f"Processing {len(messages)} messages...")

            # Extract entities
            entities_results = asyncio.run(extractor.extract_entities(messages))

            # Create decisions
            decisions_created = 0
            for msg, entities in zip(messages, entities_results):
                if entities.decision_type:  # Only create decisions for significant messages
                    decision_text = extractor.extract_decision_text(msg, entities)

                    cursor.execute("""
                        INSERT INTO decisions (
                            thread_id, timestamp, author_user_id, decision_type,
                            decision_text, affected_components, referenced_reqs
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING decision_id
                    """, (
                        msg.thread_id, msg.timestamp, msg.user_id,
                        entities.decision_type.value, decision_text,
                        entities.components, entities.requirements
                    ))

                    decision_id = cursor.fetchone()['decision_id']

                    # Store additional details
                    if entities.before_after_changes:
                        cursor.execute("""
                            INSERT INTO decision_details (decision_id, detail_name, detail_value)
                            VALUES (%s, 'before_after_changes', %s)
                        """, (decision_id, json.dumps(entities.before_after_changes)))

                    decisions_created += 1

            click.echo(f"✅ Created {decisions_created} decisions")

            # Build relationships if we have enough decisions
            if decisions_created > 1:
                cursor.execute("SELECT * FROM decisions ORDER BY timestamp")
                all_decisions = [Decision(**dict(row)) for row in cursor.fetchall()]

                relationships = graph_builder.build_relationships(all_decisions)

                for rel in relationships:
                    cursor.execute("""
                        INSERT INTO decision_relationships (
                            source_decision_id, target_decision_id, relationship_type, confidence
                        ) VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (rel.source_decision_id, rel.target_decision_id,
                          rel.relationship_type.value, rel.confidence))

                click.echo(f"✅ Created {len(relationships)} relationships")

            # Refresh materialized view
            refresh_materialized_view()

    except Exception as e:
        click.echo(f"❌ Ingestion failed: {e}")
        raise

@cli.command()
@click.option('--cleanup-failed', is_flag=True, help='Reset failed embeddings to pending')
def embed(cleanup_failed):
    """Generate embeddings for decisions."""
    if cleanup_failed:
        click.echo("🔄 Cleaning up failed embeddings...")
        pipeline = EmbeddingPipeline()
        count = pipeline.cleanup_failed_embeddings()
        click.echo(f"✅ Reset {count} failed embeddings to pending")

    click.echo("🧮 Generating embeddings...")

    try:
        pipeline = EmbeddingPipeline()

        # Get current stats
        stats = pipeline.get_embedding_stats()
        click.echo(f"Current status: {stats['pending']} pending, {stats['embedded']} embedded, {stats['failed']} failed")

        if stats['pending'] == 0:
            click.echo("No pending embeddings to process")
            return

        # Run embedding
        start_time = time.time()
        results = pipeline.run_batch_embedding()
        end_time = time.time()

        click.echo(f"✅ Processed {results['processed']} decisions in {end_time - start_time:.2f} seconds")
        click.echo(f"   Succeeded: {results['succeeded']}")
        click.echo(f"   Failed: {results['failed']}")

    except Exception as e:
        click.echo(f"❌ Embedding failed: {e}")
        raise

@cli.command()
@click.argument('user_id')
@click.argument('query')
@click.option('--limit', default=10, help='Maximum number of results')
@click.option('--days', default=30, help='Days back to search')
def query(user_id, query, limit, days):
    """Search decisions for a user."""
    click.echo(f"🔍 Searching for '{query}' (user: {user_id})...")

    try:
        retriever = HybridRetriever()
        results = retriever.search_decisions(
            query=query,
            user_id=user_id,
            time_range_days=days,
            limit=limit
        )

        if not results:
            click.echo("No results found")
            return

        click.echo(f"\nFound {len(results)} results:")
        click.echo("-" * 80)

        for i, result in enumerate(results, 1):
            click.echo(f"\n{i}. DEC-{result['decision_id']:03d} ({result['similarity_score']:.3f})")
            click.echo(f"   Author: {result['author_name']} ({result['author_role']})")
            click.echo(f"   Time: {result['timestamp'].strftime('%Y-%m-%d %H:%M')}")
            click.echo(f"   Type: {result['decision_type']}")
            click.echo(f"   Components: {', '.join(result['affected_components'])}")
            click.echo(f"   Text: {result['decision_text'][:100]}...")

            if result['relationships']:
                rel_summary = ', '.join(f"{r['relationship_type']}" for r in result['relationships'][:2])
                click.echo(f"   Related: {rel_summary}")

    except Exception as e:
        click.echo(f"❌ Query failed: {e}")
        raise

@cli.command()
@click.argument('user_id')
@click.option('--days', default=7, help='Days back to include in digest')
@click.option('--output-format', default='text', type=click.Choice(['text', 'json']), help='Output format')
def digest(user_id, days, output_format):
    """Generate personalized digest for a user."""
    click.echo(f"📊 Generating digest for {user_id} (last {days} days)...")

    try:
        generator = DigestGenerator()
        digest_result = asyncio.run(generator.generate_personalized_digest(
            user_id=user_id,
            date=datetime.now(),
            days_back=days
        ))

        if output_format == 'json':
            click.echo(json.dumps({
                'user_id': digest_result.user_id,
                'date': digest_result.date.isoformat(),
                'summary': digest_result.summary,
                'themes': digest_result.themes,
                'entries': [
                    {
                        'decision_id': e.decision_id,
                        'title': e.title,
                        'summary': e.summary,
                        'impact_summary': e.impact_summary,
                        'before_after': e.before_after,
                        'affected_components': e.affected_components,
                        'citations': e.citations,
                        'timestamp': e.timestamp.isoformat()
                    } for e in digest_result.entries
                ],
                'gaps_detected': digest_result.gaps_detected,
                'action_items': digest_result.action_items
            }, indent=2))
        else:
            formatted_digest = generator.format_digest_for_display(digest_result)
            click.echo(formatted_digest)

    except Exception as e:
        click.echo(f"❌ Digest generation failed: {e}")
        raise

@cli.command()
@click.option('--days', default=30, help='Days back to analyze')
@click.option('--output-format', default='text', type=click.Choice(['text', 'json']), help='Output format')
def gaps(days, output_format):
    """Detect gaps in decision making."""
    click.echo(f"🔍 Detecting gaps in last {days} days...")

    try:
        detector = GapDetector()
        gaps_result = detector.detect_all_gaps(days_back=days)

        total_gaps = sum(len(gaps) for gaps in gaps_result.values())
        click.echo(f"Found {total_gaps} total gaps")

        if output_format == 'json':
            # Convert datetime objects to ISO strings for JSON serialization
            json_result = {}
            for gap_type, gaps in gaps_result.items():
                json_gaps = []
                for gap in gaps:
                    json_gap = gap.copy()
                    if 'timestamp' in json_gap:
                        json_gap['timestamp'] = gap['timestamp'].isoformat()
                    if 'decisions' in json_gap:
                        for decision in json_gap['decisions']:
                            if 'timestamp' in decision:
                                decision['timestamp'] = decision['timestamp']
                    json_gaps.append(json_gap)
                json_result[gap_type] = json_gaps

            click.echo(json.dumps(json_result, indent=2))
        else:
            report = detector.generate_gap_report(gaps_result)
            click.echo(report)

    except Exception as e:
        click.echo(f"❌ Gap detection failed: {e}")
        raise

@cli.command()
@click.option('--queries', default=100, help='Number of test queries')
@click.option('--users', default=None, help='Comma-separated user IDs to test')
def benchmark(queries, users):
    """Run performance benchmarks."""
    click.echo("⚡ Running performance benchmarks...")

    try:
        retriever = HybridRetriever()

        # Test queries
        test_queries = [
            "motor torque requirements",
            "PCB design changes",
            "thermal analysis results",
            "supplier issues",
            "firmware updates",
            "assembly process",
            "requirement changes",
            "approval decisions"
        ]

        test_users = ['alice', 'bob', 'dave', 'eve'] if not users else users.split(',')

        # Benchmark search performance
        click.echo("\n🔍 Search Performance:")
        click.echo("-" * 40)

        search_times = []
        for i in range(queries):
            query = test_queries[i % len(test_queries)]
            user_id = test_users[i % len(test_users)]

            start_time = time.time()
            results = retriever.search_decisions(
                query=query,
                user_id=user_id,
                limit=20
            )
            end_time = time.time()

            search_time = (end_time - start_time) * 1000  # Convert to ms
            search_times.append(search_time)

            if i < 5:  # Show details for first few queries
                click.echo(f"Query {i+1}: {search_time:.1f}ms ({len(results)} results)")

        # Calculate statistics
        avg_time = sum(search_times) / len(search_times)
        p95_time = sorted(search_times)[int(0.95 * len(search_times))]
        p99_time = sorted(search_times)[int(0.99 * len(search_times))]

        click.echo(f"\n📊 Search Statistics ({queries} queries):")
        click.echo(f"   Average: {avg_time:.1f}ms")
        click.echo(f"   P95: {p95_time:.1f}ms")
        click.echo(f"   P99: {p99_time:.1f}ms")
        click.echo(f"   Target: <100ms ({'✅' if p95_time < 100 else '❌'})")

        # Benchmark digest generation
        click.echo("\n📊 Digest Generation Performance:")
        click.echo("-" * 40)

        generator = DigestGenerator()
        digest_times = []

        for user_id in test_users:
            start_time = time.time()
            digest_result = asyncio.run(generator.generate_personalized_digest(
                user_id=user_id,
                date=datetime.now(),
                days_back=7
            ))
            end_time = time.time()

            digest_time = end_time - start_time
            digest_times.append(digest_time)

            click.echo(f"{user_id}: {digest_time:.2f}s ({len(digest_result.entries)} entries)")

        avg_digest_time = sum(digest_times) / len(digest_times)
        click.echo(f"\nAverage digest time: {avg_digest_time:.2f}s")
        click.echo(f"Target: <5s ({'✅' if avg_digest_time < 5 else '❌'})")

        # Database statistics
        click.echo("\n💾 Database Statistics:")
        click.echo("-" * 40)

        pipeline = EmbeddingPipeline()
        embedding_stats = pipeline.get_embedding_stats()

        with get_db() as db:
            cursor = db.cursor()

            cursor.execute("SELECT COUNT(*) FROM decisions")
            decision_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM slack_messages")
            message_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM decision_relationships")
            relationship_count = cursor.fetchone()[0]

        click.echo(f"   Decisions: {decision_count}")
        click.echo(f"   Messages: {message_count}")
        click.echo(f"   Relationships: {relationship_count}")
        click.echo(f"   Embeddings: {embedding_stats}")

    except Exception as e:
        click.echo(f"❌ Benchmark failed: {e}")
        raise

@cli.command()
def status():
    """Show system status and statistics."""
    click.echo("📊 System Status")
    click.echo("=" * 50)

    try:
        # Database connection test
        with get_db() as db:
            cursor = db.cursor()

            # Basic counts
            cursor.execute("SELECT COUNT(*) FROM user_profiles")
            user_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM slack_messages")
            message_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM decisions")
            decision_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM decision_relationships")
            relationship_count = cursor.fetchone()[0]

            click.echo(f"👥 Users: {user_count}")
            click.echo(f"💬 Messages: {message_count}")
            click.echo(f"🎯 Decisions: {decision_count}")
            click.echo(f"🔗 Relationships: {relationship_count}")

            # Embedding status
            pipeline = EmbeddingPipeline()
            embedding_stats = pipeline.get_embedding_stats()

            click.echo(f"\n🧮 Embeddings:")
            for status, count in embedding_stats.items():
                if status != 'error':
                    click.echo(f"   {status}: {count}")

            # Recent activity
            cursor.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM decisions
                WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """)

            recent_activity = cursor.fetchall()
            if recent_activity:
                click.echo(f"\n📈 Recent Activity (last 7 days):")
                for date, count in recent_activity:
                    click.echo(f"   {date}: {count} decisions")

        click.echo(f"\n✅ System operational")

    except Exception as e:
        click.echo(f"❌ Status check failed: {e}")
        raise

if __name__ == '__main__':
    cli()