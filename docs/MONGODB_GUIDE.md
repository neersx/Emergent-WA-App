# MongoDB — Complete Setup & Application Guide
## WhatsApp Business Management Platform

> Everything you need to install MongoDB locally, understand the application's
> database design, run queries, and maintain the database.

---

## Table of Contents

1. [Why MongoDB?](#1-why-mongodb)
2. [Install MongoDB on macOS](#2-install-mongodb-on-macos)
3. [Start, Stop & Manage MongoDB](#3-start-stop--manage-mongodb)
4. [MongoDB Core Concepts](#4-mongodb-core-concepts)
5. [MongoDB Shell (mongosh) Basics](#5-mongodb-shell-mongosh-basics)
6. [Application Database Overview](#6-application-database-overview)
7. [All 17 Collections — Full Schema Reference](#7-all-17-collections--full-schema-reference)
8. [Indexes — Design & Rationale](#8-indexes--design--rationale)
9. [How the App Connects — Motor Driver](#9-how-the-app-connects--motor-driver)
10. [Key Query Patterns Used in the App](#10-key-query-patterns-used-in-the-app)
11. [Aggregation Pipelines](#11-aggregation-pipelines)
12. [Job Queue Pattern](#12-job-queue-pattern)
13. [TTL (Auto-Expiry) Indexes](#13-ttl-auto-expiry-indexes)
14. [Useful Maintenance Queries](#14-useful-maintenance-queries)
15. [Backup & Restore](#15-backup--restore)
16. [Performance Tips](#16-performance-tips)
17. [Common Errors & Fixes](#17-common-errors--fixes)

---

## 1. Why MongoDB?

This application uses MongoDB for several specific reasons:

| Feature | Why it matters here |
|---------|-------------------|
| **Flexible schema** | Inbound messages can be text, image, video, location, reaction — different fields per type. A fixed SQL schema would require many nullable columns or a separate table per type. |
| **Native JSON documents** | Webhook payloads from Meta arrive as JSON. Storing them as documents preserves structure exactly. |
| **Atomic `find_one_and_update`** | The job queue uses this to claim exactly one job atomically without race conditions — no `SELECT FOR UPDATE` needed. |
| **TTL indexes** | Refresh tokens and idempotency keys expire automatically — zero application-level cleanup code. |
| **Aggregation pipeline** | The analytics endpoints (timeseries, cost rollup, template performance) use MongoDB's `$group`, `$match`, `$addFields` — no separate analytics database needed. |
| **`upsert` with `$setOnInsert`** | The WABA onboarding and conversation tracking are fully idempotent using upsert — safe to call repeatedly. |
| **Motor async driver** | FastAPI is async throughout; Motor provides a native `async/await` MongoDB driver with no thread pool overhead. |

---

## 2. Install MongoDB on macOS

### 2.1 Using Homebrew (Recommended)

```bash
# Step 1 — Add the MongoDB Homebrew tap
brew tap mongodb/brew

# Step 2 — Install MongoDB Community Edition 7.0
brew install mongodb-community@7.0

# Step 3 — Verify the installation
mongod --version
# db version v7.0.x
```

### 2.2 Install mongosh (MongoDB Shell)

mongosh is installed automatically with `mongodb-community`. Verify:

```bash
mongosh --version
# 2.x.x
```

### 2.3 Default Data & Log Paths

After Homebrew install on macOS:

| Item | Path |
|------|------|
| Data directory | `/opt/homebrew/var/mongodb` (Apple Silicon) |
| Log file | `/opt/homebrew/var/log/mongodb/mongo.log` |
| Config file | `/opt/homebrew/etc/mongod.conf` |
| Homebrew service | `~/Library/LaunchAgents/homebrew.mxcl.mongodb-community.plist` |

> **Intel Mac paths** use `/usr/local/` instead of `/opt/homebrew/`.

### 2.4 Alternative — Docker

If you prefer Docker over a native install:

```bash
# Pull and run MongoDB 7
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  mongo:7.0

# Verify
docker exec -it mongodb mongosh --eval "db.runCommand({connectionStatus:1})"
```

To stop/start the container:
```bash
docker stop mongodb
docker start mongodb
```

---

## 3. Start, Stop & Manage MongoDB

### As a macOS Service (auto-starts on login)

```bash
# Start MongoDB and configure it to auto-start on login
brew services start mongodb-community@7.0

# Stop MongoDB
brew services stop mongodb-community@7.0

# Restart MongoDB
brew services restart mongodb-community@7.0

# Check status
brew services list | grep mongodb
# Expected:
# mongodb-community  started  <username>  ~/Library/LaunchAgents/...
```

### As a Foreground Process (manual, no auto-start)

```bash
# Start in foreground (Ctrl+C to stop)
mongod --config /opt/homebrew/etc/mongod.conf

# Or with explicit paths
mongod --dbpath /opt/homebrew/var/mongodb \
       --logpath /opt/homebrew/var/log/mongodb/mongo.log \
       --port 27017
```

### Verify Connection

```bash
# Quick check
mongosh --eval "db.runCommand({connectionStatus:1})" --quiet
# Expected: { ok: 1 }

# Or open the interactive shell
mongosh
# MongoDB shell version v7.0.x
# Connecting to: mongodb://127.0.0.1:27017
# >
```

---

## 4. MongoDB Core Concepts

Understanding these terms is essential before exploring the application database.

### Hierarchy

```
MongoDB Server (mongod)
  └── Database          ← "whatsapp_saas"
        └── Collection  ← like a table (e.g. "messages")
              └── Document  ← like a row (JSON object)
                    └── Field  ← like a column (key-value pair)
```

### Document (the fundamental unit)

```json
{
  "_id": "b541acc1-a0dc-477a-a78e-8c4e54125233",
  "email": "owner@demo.com",
  "role": "TenantOwner",
  "tenant_id": "fc26e509-e8f9-4969-b967-ffd49f5bd1c7",
  "created_at": "2026-07-05T10:00:00Z"
}
```

### Key Differences vs Relational Databases

| Concept | SQL (PostgreSQL, MySQL) | MongoDB |
|---------|------------------------|---------|
| Table | `CREATE TABLE users (...)` | Collection `db.users` |
| Row | Fixed columns | Flexible JSON document |
| Primary key | `id SERIAL PRIMARY KEY` | `_id` field (auto or manual) |
| Foreign key | `REFERENCES tenants(id)` | Embedded field or manual reference |
| Schema | Enforced by DDL | Optional (by convention) |
| Join | `JOIN` | `$lookup` aggregation |
| Index | `CREATE INDEX` | `db.coll.createIndex()` |
| Transaction | Multi-row ACID | Single-document atomic; multi-doc sessions |
| Auto-expire rows | `pg_cron` / scheduled jobs | TTL Index — zero code needed |

### This Application's `_id` Convention

Standard MongoDB uses `ObjectId` for `_id`. This application uses **UUID strings** instead:

```python
# In Python (backend)
import uuid
doc_id = str(uuid.uuid4())
# "f4048682-0d87-4df9-9cc9-20985c5ca3e4"
```

**Why UUIDs?** UUIDs are globally unique, portable across systems, and safe to expose in URLs. The `_id` and `id` fields always hold the same value — `id` is the API-facing field name, `_id` is MongoDB's primary key.

---

## 5. MongoDB Shell (mongosh) Basics

### Open the Shell

```bash
mongosh
```

### Switch to the Application Database

```bash
# Show all databases
show dbs

# Switch to the app database
use whatsapp_saas

# Confirm current database
db.getName()
# whatsapp_saas
```

### Essential mongosh Commands

```js
// ── Collections ──────────────────────────────────────────────
show collections          // List all collections

// ── Count ────────────────────────────────────────────────────
db.messages.countDocuments()                    // Total documents
db.messages.countDocuments({direction:"outbound"})  // With filter

// ── Find ─────────────────────────────────────────────────────
db.users.find()                                 // All documents (paginated)
db.users.findOne({email:"owner@demo.com"})      // First match
db.users.find({role:"TenantOwner"}).pretty()    // Formatted output
db.users.find({}, {email:1, role:1, _id:0})     // Project only email+role

// ── Sort & Limit ─────────────────────────────────────────────
db.messages.find().sort({created_at:-1}).limit(5)   // 5 most recent
db.messages.find().sort({created_at:1}).skip(10).limit(5) // Pagination

// ── Insert ───────────────────────────────────────────────────
db.test_coll.insertOne({name:"hello", value:42})
db.test_coll.insertMany([{a:1},{a:2},{a:3}])

// ── Update ───────────────────────────────────────────────────
db.users.updateOne(
  {email:"owner@demo.com"},
  {$set: {full_name:"Demo Owner Updated"}}
)
// updateMany, findOneAndUpdate also available

// ── Delete ───────────────────────────────────────────────────
db.test_coll.deleteOne({name:"hello"})
db.test_coll.deleteMany({a:{$lt:3}})

// ── Indexes ──────────────────────────────────────────────────
db.messages.getIndexes()          // List all indexes on collection
db.messages.createIndex({status:1})   // Create a simple index
db.messages.dropIndex("index_name")   // Drop an index

// ── Aggregate ────────────────────────────────────────────────
db.messages.aggregate([
  {$match: {direction:"outbound"}},
  {$group: {_id:"$status", count:{$sum:1}}}
])
```

### Query Operators Cheat Sheet

```js
// Comparison
{age: {$gt:18}}           // greater than
{age: {$gte:18}}          // greater than or equal
{age: {$lt:65}}           // less than
{age: {$ne:0}}            // not equal
{status: {$in:["sent","delivered"]}}   // in list
{status: {$nin:["failed"]}}            // not in list

// Logical
{$and: [{a:1},{b:2}]}     // AND
{$or:  [{a:1},{b:2}]}     // OR
{$not: {a:{$gt:5}}}       // NOT

// Field existence
{meta_message_id: {$exists:true}}    // field exists
{error: {$exists:false}}             // field absent

// Regex
{name: {$regex:"order", $options:"i"}}  // case-insensitive match

// Array
{tags: {$elemMatch:{$eq:"promo"}}}    // element in array
```

---

## 6. Application Database Overview

**Database name:** `whatsapp_saas`

```
whatsapp_saas
  ├── users                  (3 docs)   — Platform users
  ├── tenants                (2 docs)   — Client companies
  ├── refresh_tokens         (35 docs)  — Auth session tokens (TTL: 14 days)
  ├── password_resets        (0 docs)   — Password reset tokens (TTL: 30 min)
  ├── wabas                  (3 docs)   — WhatsApp Business Accounts
  ├── waba_credentials       (3 docs)   — Encrypted Meta API tokens
  ├── phone_numbers          (5 docs)   — Phone numbers per WABA
  ├── templates              (16 docs)  — Message templates
  ├── messages               (576 docs) — All inbound + outbound messages
  ├── conversations          (15 docs)  — Conversation threads
  ├── webhook_events_raw     (6 docs)   — Raw Meta webhook payloads
  ├── mq_jobs                (6 docs)   — Background job queue
  ├── usage_daily_rollup     (266 docs) — Daily cost/usage aggregates
  ├── template_perf_rollup   (36 docs)  — Template performance by month
  ├── media_assets           (0 docs)   — Downloaded media file metadata
  ├── audit_log              (7 docs)   — Immutable action trail
  └── idempotency_keys       (0 docs)   — Message dedup keys (TTL: 24h)
```

### Entity Relationships (MongoDB style)

```
tenants ─── users              (tenant_id field on users)
        ─── wabas              (tenant_id field on wabas)
        ─── usage_daily_rollup (tenant_id field)
        ─── audit_log          (tenant_id field)

wabas ──── waba_credentials    (waba_id field — 1:1)
       ─── phone_numbers       (waba_id field)
       ─── templates           (waba_id field)

phone_numbers ─── messages     (phone_number_id field)
              ─── conversations (phone_number_id field)

conversations ─── messages     (conversation_id field)

messages ─── media_assets      (message_id field)
```

> There are **no JOIN operations** in MongoDB. The application code does the join
> by making two queries in sequence when needed (e.g., fetch conversation, then fetch messages).

---

## 7. All 17 Collections — Full Schema Reference

---

### `users`
Stores all platform users across all tenants.

```json
{
  "_id": "b541acc1-a0dc-477a-a78e-8c4e54125233",
  "id": "b541acc1-a0dc-477a-a78e-8c4e54125233",
  "email": "owner@demo.com",
  "password_hash": "$2b$10$...",
  "full_name": "Demo Owner",
  "role": "TenantOwner",
  "tenant_id": "fc26e509-e8f9-4969-b967-ffd49f5bd1c7",
  "mfa_enabled": false,
  "mfa_required": false,
  "mfa_secret_encrypted": null,
  "created_at": "2026-07-05T06:36:04.591000+00:00"
}
```

**Roles:** `PlatformSuperAdmin` | `TenantOwner` | `TenantAdmin` | `Agent` | `Viewer`

**Shell queries:**
```js
// Find all users
db.users.find({}, {email:1, role:1, tenant_id:1, _id:0}).pretty()

// Find by email
db.users.findOne({email: "owner@demo.com"})

// Find all users in a tenant
db.users.find({tenant_id: "fc26e509-e8f9-4969-b967-ffd49f5bd1c7"})

// Reset a user's MFA (useful for dev/testing)
db.users.updateOne(
  {email: "owner@demo.com"},
  {$set: {mfa_enabled: false}, $unset: {mfa_secret_encrypted: ""}}
)
```

---

### `tenants`
One document per customer company.

```json
{
  "_id": "fc26e509-e8f9-4969-b967-ffd49f5bd1c7",
  "id": "fc26e509-e8f9-4969-b967-ffd49f5bd1c7",
  "name": "Demo Inc",
  "created_at": "2026-07-05T06:36:04.571000+00:00"
}
```

**Shell queries:**
```js
// List all tenants
db.tenants.find({}, {name:1, created_at:1}).pretty()

// Find tenant by name
db.tenants.findOne({name: "Demo Inc"})
```

---

### `refresh_tokens`
Opaque session tokens. Only the SHA-256 hash is stored — the raw token lives only in an httpOnly cookie.

```json
{
  "_id": "a3f1b2c4",
  "user_id": "b541acc1-a0dc-477a-a78e-8c4e54125233",
  "token_hash": "sha256hexhashofrawtoken...",
  "expires_at": "2026-07-19T06:36:04.591000+00:00",
  "revoked": false,
  "created_at": "2026-07-05T06:36:04.591000+00:00"
}
```

> **TTL Index on `expires_at`** — MongoDB automatically deletes expired tokens with no application code.

**Shell queries:**
```js
// Count active tokens for a user
db.refresh_tokens.countDocuments({
  user_id: "b541acc1-...",
  revoked: false,
  expires_at: {$gt: new Date()}
})

// Revoke all tokens for a user (force logout everywhere)
db.refresh_tokens.updateMany(
  {user_id: "b541acc1-..."},
  {$set: {revoked: true}}
)

// Clean up manually (normally handled by TTL)
db.refresh_tokens.deleteMany({expires_at: {$lt: new Date()}})
```

---

### `wabas`
WhatsApp Business Account records. Each tenant can have multiple WABAs.

```json
{
  "_id": "f4048682-0d87-4df9-9cc9-20985c5ca3e4",
  "id": "f4048682-0d87-4df9-9cc9-20985c5ca3e4",
  "tenant_id": "fc26e509-e8f9-4969-b967-ffd49f5bd1c7",
  "waba_id": "demo_waba_techcorp_001",
  "business_id": "biz_demo_waba_techcorp_001",
  "name": "TechCorp Messaging",
  "is_demo": true,
  "templates_last_synced_at": "2026-07-05T10:32:53.123000+00:00",
  "created_at": "2026-07-05T09:32:53.123000+00:00"
}
```

**Shell queries:**
```js
// All WABAs for a tenant
db.wabas.find({tenant_id: "fc26e509-..."})

// Find WABA by Meta waba_id
db.wabas.findOne({waba_id: "demo_waba_techcorp_001"})

// WABAs that haven't been synced in the last 10 minutes
const tenMinutesAgo = new Date(Date.now() - 10*60*1000).toISOString()
db.wabas.find({
  is_demo: {$ne: true},
  $or: [
    {templates_last_synced_at: {$lt: tenMinutesAgo}},
    {templates_last_synced_at: {$exists: false}}
  ]
})
```

---

### `waba_credentials`
Fernet-encrypted Meta business access tokens. Stored 1:1 with each WABA.

```json
{
  "_id": "cred_demo_waba_techcorp_001",
  "waba_id": "demo_waba_techcorp_001",
  "encrypted_business_token": "gAAAAAB...(Fernet ciphertext)...",
  "created_at": "2026-07-05T10:32:53.123000+00:00",
  "updated_at": "2026-07-05T10:32:53.123000+00:00"
}
```

> **Security:** The token is Fernet-encrypted (AES-128-CBC + HMAC-SHA256). It is **never** returned to the frontend. Decrypted in-memory only at the moment of an API call.

---

### `phone_numbers`
Each phone number associated with a WABA.

```json
{
  "_id": "3f8d9a2b-...",
  "id": "3f8d9a2b-...",
  "tenant_id": "fc26e509-...",
  "waba_id": "demo_waba_techcorp_001",
  "phone_number_id": "phone_demo_us_001",
  "display_phone_number": "+1 (555) 100-2000",
  "verified_name": "TechCorp US",
  "quality_rating": "GREEN",
  "created_at": "2026-07-05T09:32:53.123000+00:00"
}
```

**Shell queries:**
```js
// All phone numbers for a tenant
db.phone_numbers.find({tenant_id: "fc26e509-..."}, {
  display_phone_number:1, verified_name:1, quality_rating:1
})

// Find by phone_number_id (Meta's ID, not the actual number)
db.phone_numbers.findOne({phone_number_id: "phone_demo_us_001"})
```

---

### `templates`
Message templates (components are the structured JSON defining header/body/footer/buttons).

```json
{
  "_id": "a1b2c3d4-...",
  "id": "a1b2c3d4-...",
  "tenant_id": "fc26e509-...",
  "waba_id": "demo_waba_retail_001",
  "name": "order_shipped",
  "language": "en_US",
  "category": "UTILITY",
  "body": "Your order #{{1}} has shipped! Estimated delivery: {{2}}. Track at: {{3}}",
  "status": "APPROVED",
  "rejection_reason": null,
  "meta_template_id": "meta_tpl_234567890",
  "components": [
    {"type": "BODY", "text": "Your order #{{1}} has shipped!..."}
  ],
  "source": "meta",
  "created_at": "2026-06-15T08:00:00Z",
  "updated_at": "2026-06-15T08:00:00Z"
}
```

**Status values:** `PENDING` | `APPROVED` | `REJECTED` | `PAUSED` | `DISABLED`

**Shell queries:**
```js
// All APPROVED templates for a WABA
db.templates.find({
  tenant_id: "fc26e509-...",
  waba_id: "demo_waba_retail_001",
  status: "APPROVED"
}, {name:1, category:1, body:1})

// Templates by category
db.templates.find({category: "MARKETING"}).count()

// Find rejected templates with reason
db.templates.find(
  {status: "REJECTED"},
  {name:1, rejection_reason:1}
)

// Update a template status (e.g., after webhook)
db.templates.updateMany(
  {waba_id: "demo_waba_retail_001", name: "summer_sale", language: "en_US"},
  {$set: {status: "APPROVED", rejection_reason: null, updated_at: new Date().toISOString()}}
)
```

---

### `messages`
The largest and most important collection — every inbound and outbound message.

```json
{
  "_id": "8f1e2a3b-...",
  "id": "8f1e2a3b-...",
  "tenant_id": "fc26e509-...",
  "phone_number_id": "phone_demo_us_001",
  "conversation_id": "conv_phone_demo_us_001_14155550101",
  "direction": "outbound",
  "msg_type": "template",
  "to_wa_id": "14155550101",
  "template_name": "order_shipped",
  "body": null,
  "status": "delivered",
  "meta_message_id": "wamid.HBg123ABC456...",
  "pricing_category": "utility",
  "pricing_billable": true,
  "cost_amount": 0.015,
  "country_code": "US",
  "month": "2026-07",
  "created_at": "2026-07-05T09:45:00Z",
  "sent_at": "2026-07-05T09:45:01Z",
  "delivered_at": "2026-07-05T09:45:03Z",
  "read_at": null,
  "failed_at": null,
  "error": null
}
```

**Message types (`msg_type`):**
`text` | `template` | `image` | `video` | `audio` | `document` | `location` | `contacts` | `interactive` | `reaction` | `sticker`

**Status flow:** `queued` → `sent` → `delivered` → `read` (or `failed`)

**Shell queries:**
```js
// Recent messages for a tenant
db.messages.find(
  {tenant_id: "fc26e509-..."},
  {direction:1, status:1, template_name:1, created_at:1}
).sort({created_at:-1}).limit(10)

// Delivery stats
db.messages.aggregate([
  {$match: {tenant_id: "fc26e509-...", direction: "outbound"}},
  {$group: {_id: "$status", count: {$sum: 1}}}
])

// Messages in a conversation thread
db.messages.find(
  {conversation_id: "conv_phone_demo_us_001_14155550101"}
).sort({created_at:1})

// Failed messages with reasons
db.messages.find(
  {status: "failed", error: {$exists: true}},
  {to_wa_id:1, error:1, failed_at:1}
)

// Messages by template name
db.messages.find(
  {template_name: "order_shipped"},
  {to_wa_id:1, status:1, created_at:1}
)

// This month's messages (uses monthly partition index)
db.messages.find(
  {tenant_id: "fc26e509-...", month: "2026-07"}
).sort({created_at:-1})
```

---

### `conversations`
One document per (phone_number_id, contact_wa_id) pair. Tracks the service window state.

```json
{
  "_id": "conv_phone_demo_us_001_14155550101",
  "id": "conv_phone_demo_us_001_14155550101",
  "tenant_id": "fc26e509-...",
  "phone_number_id": "phone_demo_us_001",
  "contact_wa_id": "14155550101",
  "status": "open",
  "assigned_to": null,
  "unread_count": 2,
  "last_inbound_at": "2026-07-05T09:44:00Z",
  "free_entry_point_expires_at": null,
  "created_at": "2026-06-10T08:00:00Z",
  "updated_at": "2026-07-05T09:44:00Z"
}
```

**Shell queries:**
```js
// Open conversations with unread messages
db.conversations.find(
  {tenant_id: "fc26e509-...", status: "open", unread_count: {$gt: 0}},
  {contact_wa_id:1, unread_count:1, last_inbound_at:1}
).sort({last_inbound_at:-1})

// Conversations with open service window (last inbound < 24h ago)
const cutoff = new Date(Date.now() - 24*60*60*1000).toISOString()
db.conversations.find({
  tenant_id: "fc26e509-...",
  last_inbound_at: {$gt: cutoff}
})

// Close a conversation
db.conversations.updateOne(
  {_id: "conv_phone_demo_us_001_14155550101"},
  {$set: {status: "closed", closed_at: new Date().toISOString()}}
)

// Reset unread count (done when agent views thread)
db.conversations.updateOne(
  {_id: "conv_phone_demo_us_001_14155550101"},
  {$set: {unread_count: 0}}
)
```

---

### `usage_daily_rollup`
Pre-aggregated cost/usage data — updated incrementally on every message delivery.

```json
{
  "_id": "fc26e509-...:2026-07-05:marketing:US",
  "tenant_id": "fc26e509-...",
  "day": "2026-07-05",
  "category": "marketing",
  "country_code": "US",
  "delivered_count": 45,
  "billable_count": 45,
  "free_count": 0,
  "cost_amount": 1.1250,
  "cost_currency": "USD",
  "updated_at": "2026-07-05T10:00:00Z"
}
```

> **Pattern:** The `_id` is a composite key `tenant_id:day:category:country_code`. This makes the upsert operation idempotent — you can call `update_one(..., upsert=True)` any number of times and it will correctly accumulate totals.

**Shell queries:**
```js
// Total cost by category for a tenant (last 30 days)
const since = new Date(Date.now() - 30*24*60*60*1000).toISOString().slice(0,10)
db.usage_daily_rollup.aggregate([
  {$match: {tenant_id: "fc26e509-...", day: {$gte: since}}},
  {$group: {
    _id: "$category",
    total_cost: {$sum: "$cost_amount"},
    total_delivered: {$sum: "$delivered_count"},
    total_billable: {$sum: "$billable_count"}
  }},
  {$sort: {total_cost: -1}}
])

// Cost by country
db.usage_daily_rollup.aggregate([
  {$match: {tenant_id: "fc26e509-...", day: {$gte: since}}},
  {$group: {_id: "$country_code", cost: {$sum: "$cost_amount"}}},
  {$sort: {cost: -1}}
])

// Month-to-date spend
const monthStart = new Date().toISOString().slice(0,7) + "-01"
db.usage_daily_rollup.aggregate([
  {$match: {tenant_id: "fc26e509-...", day: {$gte: monthStart}}},
  {$group: {_id: null, mtd_cost: {$sum: "$cost_amount"}}}
])
```

---

### `mq_jobs`
MongoDB-backed async job queue. All heavy processing happens here asynchronously.

```json
{
  "_id": "9a8b7c6d-...",
  "type": "process_webhook",
  "payload": {"event_id": "e1f2a3b4-..."},
  "status": "done",
  "attempts": 1,
  "created_at": "2026-07-05T09:45:00Z",
  "claimed_at": "2026-07-05T09:45:00Z",
  "completed_at": "2026-07-05T09:45:01Z",
  "last_error": null
}
```

**Status:** `queued` → `processing` → `done` (or `failed`)

**Shell queries:**
```js
// Queue depth
db.mq_jobs.aggregate([
  {$group: {_id: "$status", count: {$sum: 1}}}
])

// Stuck jobs (processing for > 60 seconds)
const stale = new Date(Date.now() - 60000).toISOString()
db.mq_jobs.find({
  status: "processing",
  claimed_at: {$lt: stale}
})

// Failed jobs with errors
db.mq_jobs.find({status: "failed"}, {type:1, last_error:1, attempts:1})

// Clear all completed jobs (housekeeping)
db.mq_jobs.deleteMany({status: "done"})
```

---

### `webhook_events_raw`
Raw Meta webhook payloads. Stored immediately on receipt for audit and reprocessing.

```json
{
  "_id": "e1f2a3b4-...",
  "payload": {"object": "whatsapp_business_account", "entry": [...]},
  "signature_ok": true,
  "received_at": "2026-07-05T09:45:00Z",
  "processed_at": "2026-07-05T09:45:01Z",
  "status": "received"
}
```

**Shell queries:**
```js
// Unprocessed webhooks
db.webhook_events_raw.find({status: {$ne: "processed"}})

// Recent webhooks
db.webhook_events_raw.find().sort({received_at:-1}).limit(10)

// Reprocess a webhook (reset status)
db.webhook_events_raw.updateOne(
  {_id: "e1f2a3b4-..."},
  {$set: {status: "received", processed_at: null}}
)
// Then add a new mq_jobs entry to trigger reprocessing
db.mq_jobs.insertOne({
  _id: "new-uuid",
  type: "process_webhook",
  payload: {event_id: "e1f2a3b4-..."},
  status: "queued",
  attempts: 0,
  created_at: new Date().toISOString(),
  claimed_at: null,
  last_error: null
})
```

---

### `audit_log`
Immutable record of significant actions. Never updated — only inserted.

```json
{
  "_id": "c4d5e6f7-...",
  "tenant_id": "fc26e509-...",
  "actor_user_id": "b541acc1-...",
  "action": "message.send",
  "metadata": {"template": "order_shipped", "to": "14155550101"},
  "created_at": "2026-07-05T09:45:00Z"
}
```

**Shell queries:**
```js
// Recent actions for a tenant
db.audit_log.find({tenant_id: "fc26e509-..."}).sort({created_at:-1}).limit(20)

// All cross-tenant elevated reads (PlatformSuperAdmin)
db.audit_log.find({action: {$regex: "platform.elevated"}})
  .sort({created_at:-1})
```

---

## 8. Indexes — Design & Rationale

```
┌──────────────────────┬────────────────────────────────────────────┬──────────────────────────────────┐
│ Collection           │ Index                                      │ Why it exists                    │
├──────────────────────┼────────────────────────────────────────────┼──────────────────────────────────┤
│ users                │ unique(email)                              │ Prevent duplicate accounts        │
│ users                │ (tenant_id)                                │ List users by tenant              │
│ refresh_tokens       │ unique(token_hash)                         │ Fast token lookup on every request│
│ refresh_tokens       │ TTL(expires_at, expireAfterSeconds=0)      │ Auto-delete expired tokens        │
│ refresh_tokens       │ (user_id)                                  │ Revoke all tokens for a user      │
│ wabas                │ unique(waba_id)                            │ Meta waba_id is globally unique   │
│ wabas                │ (tenant_id)                                │ List WABAs for a tenant           │
│ phone_numbers        │ unique(phone_number_id)                    │ Meta phone_number_id is unique    │
│ phone_numbers        │ (tenant_id)                                │ List phones for a tenant          │
│ templates            │ unique(tenant+waba+name+language)          │ Prevent duplicate templates       │
│ templates            │ (tenant_id, waba_id)                       │ List templates for a WABA         │
│ templates            │ (meta_template_id) sparse                  │ Look up template by Meta ID       │
│ messages             │ (tenant_id, created_at DESC)               │ Default list query                │
│ messages             │ (tenant_id, conversation_id, created_at)   │ Fetch thread in order             │
│ messages             │ (tenant_id, month, created_at DESC)        │ Monthly partition queries         │
│ messages             │ (meta_message_id) sparse                   │ Update message on webhook         │
│ messages             │ (idempotency_key) sparse                   │ Dedup on send                     │
│ conversations        │ (tenant_id)                                │ List conversations for tenant     │
│ conversations        │ (phone_number_id, contact_wa_id)           │ Upsert conversation on inbound    │
│ usage_daily_rollup   │ (tenant_id, day DESC)                      │ Usage dashboard queries           │
│ usage_daily_rollup   │ (day DESC)                                 │ Platform cross-tenant dashboard   │
│ idempotency_keys     │ unique(tenant_id, key)                     │ Prevent duplicate sends           │
│ idempotency_keys     │ TTL(created_at, expireAfterSeconds=86400)  │ Auto-delete after 24 hours        │
│ audit_log            │ (tenant_id, created_at DESC)               │ Audit log queries                 │
│ media_assets         │ unique(tenant_id, meta_media_id)           │ Idempotent media download         │
│ mq_jobs              │ (status, claimed_at)                       │ Atomic job claiming               │
└──────────────────────┴────────────────────────────────────────────┴──────────────────────────────────┘
```

### Inspect indexes from mongosh

```js
// All indexes on messages
db.messages.getIndexes()

// Check if a query is using an index (explain plan)
db.messages.find({tenant_id: "fc26e509-..."}).explain("executionStats")
// Look for: "stage": "IXSCAN" (good) vs "COLLSCAN" (bad — no index used)

// Index stats (usage counts)
db.messages.aggregate([{$indexStats:{}}])
```

---

## 9. How the App Connects — Motor Driver

The backend uses **Motor**, the official async Python MongoDB driver (wraps `pymongo` for `asyncio`).

### Connection setup (`app/db.py`)

```python
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None

def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        _db = _client["whatsapp_saas"]   # DB_NAME from env
    return _db
```

### Environment variable

```ini
# backend/.env
MONGO_URL=mongodb://localhost:27017
DB_NAME=whatsapp_saas
```

### How routes use the database

```python
from .db import get_db

@router.get("/conversations")
async def list_conversations(p: Principal = Depends(require_tenant)):
    db = get_db()                              # get the database handle
    docs = await db.conversations              # access a collection
               .find({"tenant_id": p.tenant_id})  # filter by tenant (RLS)
               .sort("last_inbound_at", -1)    # sort
               .limit(50)
               .to_list(50)                    # execute and return list
    return docs
```

### Indexes are created at startup

```python
# app/db.py — called once when FastAPI starts
async def ensure_indexes() -> None:
    db = get_db()
    await db.users.create_indexes([
        IndexModel([("email", ASCENDING)], unique=True, name="uniq_email"),
        IndexModel([("tenant_id", ASCENDING)], name="by_tenant"),
    ])
    # ... all 17 collections
```

---

## 10. Key Query Patterns Used in the App

### 1. Tenant-Scoped Query (RLS Pattern)

Every query includes `tenant_id` from the authenticated user's JWT:

```python
# CORRECT — always scope to tenant
docs = await db.messages.find({"tenant_id": p.tenant_id}).to_list(50)

# WRONG — never do a global query (unless PlatformSuperAdmin + audited)
docs = await db.messages.find({}).to_list(50)
```

### 2. Idempotent Upsert with `$setOnInsert`

Used for WABA onboarding, conversation tracking, usage rollup — safe to call multiple times:

```python
await db.conversations.update_one(
    # Filter: the "identity" of the document
    {"id": conv_id, "tenant_id": tenant_id},
    {
        # $set runs EVERY time (updates mutable fields)
        "$set": {"last_inbound_at": now, "updated_at": now},
        # $inc runs EVERY time (increments counters)
        "$inc": {"unread_count": 1},
        # $setOnInsert runs ONLY on first insert
        "$setOnInsert": {
            "_id": conv_id, "id": conv_id,
            "tenant_id": tenant_id,
            "status": "open",
            "created_at": now,
        },
    },
    upsert=True,  # Create if not exists, update if exists
)
```

### 3. Atomic Job Claiming

The background worker uses `find_one_and_update` to claim exactly one job atomically:

```python
job = await db.mq_jobs.find_one_and_update(
    {
        "$or": [
            {"status": "queued"},
            {"status": "processing", "claimed_at": {"$lt": stale_cutoff}},
        ],
        "attempts": {"$lt": 5},
    },
    {
        "$set": {"status": "processing", "claimed_at": now},
        "$inc": {"attempts": 1},
    },
    sort=[("created_at", 1)],   # FIFO
    return_document=True,
)
# Only one worker gets this job — guaranteed by MongoDB atomicity
```

### 4. Incremental Rollup Update

Cost data is accumulated incrementally — no batch recalculation needed:

```python
await db.usage_daily_rollup.update_one(
    {"_id": f"{tenant_id}:{day}:{category}:{country}"},
    {
        "$inc": {
            "delivered_count": 1,
            "billable_count": 1 if billable else 0,
            "free_count": 0 if billable else 1,
            "cost_amount": cost,
        },
        "$setOnInsert": {
            "_id": key,
            "tenant_id": tenant_id,
            "day": day,
            "category": category,
            "country_code": country,
            "cost_currency": "USD",
            "created_at": now,
        },
        "$set": {"updated_at": now},
    },
    upsert=True,
)
```

---

## 11. Aggregation Pipelines

MongoDB aggregation processes documents through a pipeline of stages.

### Template Performance Stats

```js
db.messages.aggregate([
  // Stage 1: Filter
  {$match: {
    tenant_id: "fc26e509-...",
    direction: "outbound",
    template_name: {$ne: null},
    created_at: {$gte: "2026-06-01"}
  }},
  // Stage 2: Group by template
  {$group: {
    _id: "$template_name",
    sent: {$sum: 1},
    delivered: {$sum: {$cond: [{$in: ["$status", ["delivered","read"]]}, 1, 0]}},
    read: {$sum: {$cond: [{$eq: ["$status", "read"]}, 1, 0]}},
    failed: {$sum: {$cond: [{$eq: ["$status", "failed"]}, 1, 0]}}
  }},
  // Stage 3: Sort by most sent
  {$sort: {sent: -1}},
  // Stage 4: Limit
  {$limit: 10}
])
```

### Daily Message Timeseries

```js
db.messages.aggregate([
  {$match: {tenant_id: "fc26e509-...", created_at: {$gte: "2026-06-01"}}},
  // Extract YYYY-MM-DD from ISO string
  {$addFields: {day: {$substr: ["$created_at", 0, 10]}}},
  {$group: {
    _id: {day: "$day", direction: "$direction", status: "$status"},
    count: {$sum: 1}
  }}
])
```

### Cross-Tenant Cost Summary (Platform admin)

```js
db.usage_daily_rollup.aggregate([
  {$match: {day: {$gte: "2026-06-01"}}},
  {$group: {
    _id: "$tenant_id",
    total_cost: {$sum: "$cost_amount"},
    total_delivered: {$sum: "$delivered_count"}
  }},
  {$sort: {total_cost: -1}}
])
```

---

## 12. Job Queue Pattern

The application implements a **durable job queue** using a single MongoDB collection — no Redis or RabbitMQ needed.

### How it works

```
                Enqueue                     Claim (atomic)
API handler ─────────► mq_jobs {            Worker ───────► find_one_and_update
                          status: "queued"  ◄──────────────  (status: "queued" → "processing")
                        }
                                                    │
                                                    ▼
                                             Process job
                                                    │
                                            ┌───────┴────────┐
                                            ▼                ▼
                                         complete          fail
                                     {status:"done"}  {status:"failed",
                                                        last_error: "..."}
```

### Visibility timeout — stale job recovery

If the worker crashes mid-job, the job stays in `processing` status. The `claimed_at` field enables recovery — any job stuck in `processing` for more than 60 seconds is re-claimable:

```js
// Find stuck jobs
const stale = new Date(Date.now() - 60000).toISOString()
db.mq_jobs.find({
  status: "processing",
  claimed_at: {$lt: stale}
})
```

---

## 13. TTL (Auto-Expiry) Indexes

TTL indexes automatically delete documents when a date field passes the threshold.

### Configured TTL indexes

```js
// refresh_tokens — expire when expires_at passes
db.refresh_tokens.createIndex(
  {expires_at: 1},
  {expireAfterSeconds: 0}   // delete when expires_at <= current time
)

// password_resets — same pattern
db.password_resets.createIndex(
  {expires_at: 1},
  {expireAfterSeconds: 0}
)

// idempotency_keys — expire 24 hours after creation
db.idempotency_keys.createIndex(
  {created_at: 1},
  {expireAfterSeconds: 86400}  // 24 * 60 * 60
)
```

> **How it works:** MongoDB's TTL monitor runs every 60 seconds and deletes any document where `field_value + expireAfterSeconds <= now`. No cron jobs or application-level cleanup needed.

```js
// Check TTL index on refresh_tokens
db.refresh_tokens.getIndexes()
// Look for: "expireAfterSeconds": 0
```

---

## 14. Useful Maintenance Queries

### Health Check

```js
// Connection status
db.runCommand({connectionStatus: 1})

// Server status
db.serverStatus()

// Database stats
db.stats()

// Collection sizes
db.messages.stats()
// Shows: count, avgObjSize, storageSize, totalIndexSize
```

### Data Exploration

```js
// Count all documents per collection
db.getCollectionNames().forEach(c => {
  print(c + ": " + db[c].countDocuments())
})

// Find oldest and newest message
db.messages.findOne({}, {created_at:1}).sort({created_at:1})
db.messages.findOne({}, {created_at:1}).sort({created_at:-1})

// Storage used per collection (sorted)
db.getCollectionNames()
  .map(c => ({name:c, size: db[c].stats().storageSize}))
  .sort((a,b) => b.size - a.size)
  .forEach(x => print(x.name + ": " + (x.size/1024).toFixed(1) + " KB"))
```

### Data Cleanup

```js
// Remove demo seed data (keep only real WABAs)
db.wabas.deleteMany({is_demo: true})

// Remove all completed jobs (keep last 7 days)
const week = new Date(Date.now() - 7*24*60*60*1000).toISOString()
db.mq_jobs.deleteMany({status: "done", completed_at: {$lt: week}})

// Reset conversation unread counts
db.conversations.updateMany({}, {$set: {unread_count: 0}})
```

### Full Database Reset (Development Only)

```js
// ⚠️ DROPS ALL DATA — development use only
use whatsapp_saas
db.dropDatabase()
// Restart the backend — it will re-seed the database automatically
```

---

## 15. Backup & Restore

### Backup the application database

```bash
# Full backup to a directory
mongodump \
  --uri="mongodb://localhost:27017/whatsapp_saas" \
  --out="./backup/$(date +%Y-%m-%d)"

# Compressed backup
mongodump \
  --uri="mongodb://localhost:27017/whatsapp_saas" \
  --gzip \
  --archive="./backup/whatsapp_saas_$(date +%Y-%m-%d).gz"
```

### Restore from backup

```bash
# Restore from directory
mongorestore \
  --uri="mongodb://localhost:27017" \
  --db="whatsapp_saas" \
  "./backup/2026-07-05/whatsapp_saas/"

# Restore from compressed archive
mongorestore \
  --uri="mongodb://localhost:27017" \
  --gzip \
  --archive="./backup/whatsapp_saas_2026-07-05.gz"
```

### Export / Import specific collections (CSV/JSON)

```bash
# Export messages to JSON
mongoexport \
  --uri="mongodb://localhost:27017/whatsapp_saas" \
  --collection=messages \
  --out=messages_export.json

# Export usage rollup to CSV
mongoexport \
  --uri="mongodb://localhost:27017/whatsapp_saas" \
  --collection=usage_daily_rollup \
  --type=csv \
  --fields=day,category,country_code,delivered_count,billable_count,cost_amount \
  --out=usage_export.csv

# Import from JSON
mongoimport \
  --uri="mongodb://localhost:27017/whatsapp_saas" \
  --collection=messages \
  --file=messages_export.json
```

---

## 16. Performance Tips

### 1. Always explain your queries

```js
// Check if query is using an index
db.messages.find({
  tenant_id: "fc26e509-...",
  status: "delivered"
}).explain("executionStats")

// Key fields to check:
// "stage": "IXSCAN"     → good (uses index)
// "stage": "COLLSCAN"   → bad (full scan, slow)
// "nReturned": 10        → documents returned
// "totalDocsExamined": 10 → best case (equals nReturned)
```

### 2. Projection — only fetch what you need

```js
// BAD — fetches entire document including large fields
db.messages.find({tenant_id: "..."})

// GOOD — only fetch needed fields
db.messages.find(
  {tenant_id: "..."},
  {direction:1, status:1, created_at:1, template_name:1, _id:0}
)
```

### 3. Avoid large `in` arrays

```js
// BAD — $in with thousands of IDs
db.messages.find({_id: {$in: [/* 10000 ids */]}})

// GOOD — query by relationship field instead
db.messages.find({conversation_id: "conv_..."})
```

### 4. Use the right index for time-based queries

```js
// The by_tenant_month_time index is optimal for monthly queries
db.messages.find({
  tenant_id: "fc26e509-...",
  month: "2026-07"           // ← this hits the month index
}).sort({created_at: -1})

// vs. the by_tenant_time index for arbitrary date ranges
db.messages.find({
  tenant_id: "fc26e509-...",
  created_at: {$gte: "2026-07-01", $lt: "2026-07-05"}
})
```

---

## 17. Common Errors & Fixes

### `ServerSelectionTimeoutError: localhost:27017`

MongoDB is not running.
```bash
brew services start mongodb-community@7.0
```

### `WriteError: Updating the path 'field' would create a conflict`

You're using both `$set` and `$setOnInsert` (or `$inc`) on the same field path.

```python
# WRONG — unread_count in both $inc and $setOnInsert
{
    "$inc": {"unread_count": 1},
    "$setOnInsert": {"unread_count": 0}  # conflict!
}

# CORRECT — unread_count only in $inc ($inc sets to 1 on insert)
{
    "$inc": {"unread_count": 1},
    "$setOnInsert": {"status": "open"}   # no conflict
}
```

### `DuplicateKeyError: E11000 duplicate key error`

Trying to insert a document with a value that violates a unique index.

```js
// Check which index caused it
db.users.getIndexes()
// Common causes: duplicate email, duplicate waba_id, duplicate template (tenant+waba+name+lang)

// Use upsert instead of insert for idempotent operations
await db.users.update_one({"email": email}, {"$setOnInsert": doc}, upsert=True)
```

### `ValidationError: value is not a valid Fernet key`

The `TOKEN_ENCRYPTION_KEY` in `.env` is not a valid Fernet key.
```bash
python3 -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

### TTL index not deleting expired documents

TTL monitor runs every 60 seconds — there may be a delay. Also check:
```js
// Verify TTL index is configured correctly
db.refresh_tokens.getIndexes()
// Should show: "expireAfterSeconds": 0

// Check if document's expires_at is in the past
db.refresh_tokens.find({expires_at: {$lt: new Date()}})
```

---

## Quick Reference Card

```
┌──────────────────────────────────────────────────────────────────────┐
│                 MongoDB Quick Reference                               │
├──────────────────────────────────────────────────────────────────────┤
│  Start MongoDB    brew services start mongodb-community@7.0           │
│  Stop MongoDB     brew services stop mongodb-community@7.0            │
│  Open shell       mongosh                                             │
│  Use app DB       use whatsapp_saas                                   │
│  List collections show collections                                    │
│  Drop database    db.dropDatabase()  ← DESTRUCTIVE                   │
├──────────────────────────────────────────────────────────────────────┤
│  Connection URL   mongodb://localhost:27017                           │
│  Database         whatsapp_saas                                       │
│  Collections      17 (see list above)                                 │
│  Total documents  ~1000 (with demo seed data)                        │
├──────────────────────────────────────────────────────────────────────┤
│  Primary key      UUID string in _id and id fields                   │
│  Tenant filter    Always include: {tenant_id: p.tenant_id}            │
│  Date format      ISO 8601 strings: "2026-07-05T10:00:00Z"           │
│  TTL collections  refresh_tokens (14d) · password_resets (30m)       │
│                   idempotency_keys (24h)                               │
└──────────────────────────────────────────────────────────────────────┘
```

---

*WhatsApp Business Management Platform · MongoDB Guide · July 2026*
