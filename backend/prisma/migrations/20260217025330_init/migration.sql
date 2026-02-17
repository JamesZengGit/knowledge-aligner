-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "user_name" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "owned_components" TEXT NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "decisions" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "decision_id" TEXT NOT NULL,
    "thread_id" TEXT NOT NULL,
    "timestamp" DATETIME NOT NULL,
    "author_user_id" TEXT NOT NULL,
    "author_name" TEXT NOT NULL,
    "author_role" TEXT NOT NULL,
    "decision_type" TEXT NOT NULL,
    "decision_text" TEXT NOT NULL,
    "affected_components" TEXT NOT NULL,
    "referenced_reqs" TEXT NOT NULL,
    "similarity_score" REAL,
    "embedding_status" TEXT NOT NULL DEFAULT 'pending',
    "before_state" JSONB,
    "after_state" JSONB,
    CONSTRAINT "decisions_author_user_id_fkey" FOREIGN KEY ("author_user_id") REFERENCES "users" ("user_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "decision_relationships" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "source_id" INTEGER NOT NULL,
    "target_id" INTEGER NOT NULL,
    "relationship_type" TEXT NOT NULL,
    "confidence" REAL NOT NULL DEFAULT 0.0,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "decision_relationships_source_id_fkey" FOREIGN KEY ("source_id") REFERENCES "decisions" ("id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "decision_relationships_target_id_fkey" FOREIGN KEY ("target_id") REFERENCES "decisions" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "gaps" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "type" TEXT NOT NULL,
    "severity" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "decision_id" INTEGER,
    "assignee_id" TEXT,
    "priority" INTEGER NOT NULL DEFAULT 5,
    "status" TEXT NOT NULL DEFAULT 'open',
    "recommendation" TEXT NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL,
    "resolved_at" DATETIME,
    CONSTRAINT "gaps_decision_id_fkey" FOREIGN KEY ("decision_id") REFERENCES "decisions" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "gaps_assignee_id_fkey" FOREIGN KEY ("assignee_id") REFERENCES "users" ("user_id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "slack_messages" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "message_id" TEXT NOT NULL,
    "channel_id" TEXT NOT NULL,
    "thread_id" TEXT,
    "user_id" TEXT NOT NULL,
    "message_text" TEXT NOT NULL,
    "timestamp" DATETIME NOT NULL,
    "processed" BOOLEAN NOT NULL DEFAULT false,
    "decision_id" INTEGER,
    CONSTRAINT "slack_messages_decision_id_fkey" FOREIGN KEY ("decision_id") REFERENCES "decisions" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "chat_messages" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "message" TEXT NOT NULL,
    "response" TEXT,
    "context_data" JSONB,
    "timestamp" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "chat_messages_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users" ("user_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "system_config" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "key" TEXT NOT NULL,
    "value" JSONB NOT NULL,
    "description" TEXT,
    "updated_at" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "search_metrics" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "query" TEXT NOT NULL,
    "result_count" INTEGER NOT NULL,
    "response_time_ms" REAL NOT NULL,
    "query_type" TEXT NOT NULL,
    "timestamp" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "component_index" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "component" TEXT NOT NULL,
    "updated_at" DATETIME NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "users_user_id_key" ON "users"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "decisions_decision_id_key" ON "decisions"("decision_id");

-- CreateIndex
CREATE UNIQUE INDEX "decision_relationships_source_id_target_id_relationship_type_key" ON "decision_relationships"("source_id", "target_id", "relationship_type");

-- CreateIndex
CREATE UNIQUE INDEX "slack_messages_message_id_key" ON "slack_messages"("message_id");

-- CreateIndex
CREATE UNIQUE INDEX "system_config_key_key" ON "system_config"("key");

-- CreateIndex
CREATE UNIQUE INDEX "component_index_component_key" ON "component_index"("component");
