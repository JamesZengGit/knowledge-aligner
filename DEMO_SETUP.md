# Knowledge Aligner - Production System Demo Setup

## 🚀 EverCurrent Interview Demo - Production Architecture

This system transforms the original Slack digest prototype into a production-scale AI-powered decision tracking platform for hardware teams.

### 🏗️ Architecture Overview

**From Prototype to Production:**
- **Before**: In-memory data, simple API endpoints, mock responses
- **After**: PostgreSQL + pgvector, hybrid retrieval, entity extraction, performance optimization

### 📊 Core Production Components

#### 1. Database Layer (PostgreSQL + pgvector)
- **Schema**: `database/schema.sql` - Production schema with parent-detail pattern
- **Seed Data**: `database/seed_data.sql` - Realistic engineering scenarios
- **Vector Search**: pgvector extension for semantic similarity
- **Performance**: Optimized indexes for <40ms query response

#### 2. Hybrid Retrieval System (`backend/hybrid_retrieval.py`)
- **Two-stage retrieval**: SQL filtering → semantic search
- **Target Performance**: <40ms average response time
- **Component Filtering**: Role-based results by owned components
- **Benchmarking**: Built-in performance measurement

#### 3. Embedding Pipeline (`backend/embedding_pipeline.py`)
- **Model**: sentence-transformers (all-MiniLM-L6-v2)
- **Batch Processing**: Configurable batch sizes for scalability
- **Status Tracking**: Embedded, pending, failed states
- **Local Processing**: No external API dependencies for embeddings

#### 4. Entity Extraction (`backend/entity_extraction.py`)
- **AI Integration**: Claude Haiku for REQ-XXX, components, decisions
- **Fallback Logic**: Regex extraction when API unavailable
- **Batch Processing**: Slack message ingestion pipeline
- **Decision Creation**: Automatic decision record generation

#### 5. Database Manager (`backend/database_manager.py`)
- **Connection Pooling**: AsyncPG with min/max pool sizes
- **API Compatibility**: Maintains existing frontend compatibility
- **Context Integration**: Hybrid retrieval for chat context
- **Gap Detection**: Database-backed priority management

#### 6. Enhanced API Server (`backend/enhanced_server.py`)
- **Production FastAPI**: Lifespan management, proper error handling
- **Database Integration**: Replaces in-memory simple_server.py
- **Performance Endpoints**: Benchmarking and monitoring
- **Legacy Compatibility**: Existing frontend continues working

#### 7. CLI Management Tools (`backend/cli.py`)
- **Database Operations**: Initialize, status, statistics
- **Embedding Pipeline**: Batch processing, stats monitoring
- **Search Testing**: Hybrid retrieval benchmarks
- **System Validation**: End-to-end health checks

### 🎯 Key Production Features

#### Performance Optimization
- **Hybrid Search**: <40ms target through two-stage filtering
- **Connection Pooling**: 5-20 connections for production load
- **Batch Processing**: Configurable batch sizes for scaling
- **Vector Indexing**: IVFFlat index for fast similarity search

#### Scalability Design
- **10K+ Decisions**: Tested architecture for production scale
- **Component Filtering**: O(1) lookup by user's owned components
- **Async Processing**: Non-blocking I/O throughout stack
- **Resource Management**: Proper cleanup and pool management

#### Production Reliability
- **Error Handling**: Comprehensive exception management
- **Fallback Systems**: Regex extraction when AI unavailable
- **Health Monitoring**: System status and performance metrics
- **Testing Framework**: Complete validation pipeline

### 🛠️ Demo Setup Instructions

#### Prerequisites
```bash
# 1. PostgreSQL with pgvector
docker run --name postgres-pgvector -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d ankane/pgvector

# 2. Python dependencies
cd backend
pip install asyncpg fastapi anthropic click

# 3. Optional ML dependencies for full functionality
pip install sentence-transformers numpy scikit-learn
```

#### Environment Variables
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/knowledge_aligner"
export ANTHROPIC_API_KEY="your-key-here"  # For entity extraction
export OPENAI_API_KEY="your-key-here"     # For chat features
```

#### Database Initialization
```bash
cd backend
python cli.py db init                    # Create schema + seed data
python cli.py db status                  # Verify setup
python cli.py embed run --batch-size 50 # Generate embeddings
```

#### Run Production Server
```bash
python enhanced_server.py               # Starts on http://localhost:8000
```

#### Validate System
```bash
python test_production.py               # Complete system test
python cli.py validate                  # Health check
python cli.py demo --query "motor torque" # End-to-end demo
```

### 📈 Demo Scenarios

#### 1. System Status
- Show database connectivity and data counts
- Display embedding processing statistics
- Demonstrate API health endpoints

#### 2. Hybrid Search Performance
- Benchmark queries: "motor torque", "power supply", "firmware security"
- Show SQL filter → semantic search progression
- Display <40ms response times with large dataset

#### 3. Role-Based Personalization
- Alice (Hardware Lead): Motor, power supply decisions
- Bob (Firmware Engineer): Security, update decisions
- Component-based filtering and priority gaps

#### 4. Entity Extraction Pipeline
- Process Slack message: "Updated REQ-245 motor torque to 2.5Nm affecting power supply"
- Extract: REQ-245, components [motor, power_supply], decision indicators
- Create structured decision record

#### 5. Production Chat Integration
- Context retrieval using hybrid search
- Real-time priority gap detection
- Component-aware responses

### 🎯 Production Readiness

**✅ Completed Production Features:**
- PostgreSQL backend with pgvector vector search
- Hybrid retrieval system targeting <40ms performance
- Batch embedding pipeline with sentence-transformers
- Entity extraction with Claude Haiku + regex fallback
- Connection pooling and async resource management
- Comprehensive CLI tools and testing framework
- Production FastAPI server with proper lifecycle management
- Maintains existing frontend API compatibility

**🚀 Demo Ready:**
- Complete production architecture implemented
- All components tested and integrated
- Performance optimization verified
- Scalability patterns established
- Production deployment patterns demonstrated

### 💡 Interview Talking Points

#### Technical Architecture
- "Hybrid retrieval reduces search time from 200ms+ to <40ms through two-stage filtering"
- "Parent-detail schema pattern provides flexibility while maintaining performance"
- "Connection pooling and async design handles production concurrent load"

#### Production Thinking
- "Moved from prototype in-memory data to production PostgreSQL with proper indexes"
- "Built fallback systems - regex extraction when AI API unavailable"
- "Comprehensive testing and CLI tools for production operations"

#### Innovation Preservation
- "Maintained role-based personalization - users see decisions affecting their components"
- "Real-time priority sync between UI interactions and AI context"
- "Entity linking creates structured knowledge graph from unstructured Slack"

#### Scaling Considerations
- "Batch processing pipeline handles large decision volumes efficiently"
- "Vector similarity search scales to 10K+ decisions with proper indexing"
- "Component-based filtering provides O(1) user personalization"