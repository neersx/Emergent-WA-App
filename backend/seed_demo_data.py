"""
Comprehensive demo data seeder for the WhatsApp Business Platform.
Populates all collections with realistic data for demo/visualization purposes.

Run: cd /app/backend && python seed_demo_data.py
"""
import asyncio
import random
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.crypto_utils import encrypt

random.seed(42)  # reproducible

# ─── IDs ─────────────────────────────────────────────────────────────────────

WABA_1 = "waba_demo_techcorp_001"
WABA_2 = "waba_demo_retail_001"

PHONE_1 = "phone_demo_us_001"   # +1 555-100-2000  (WABA_1)
PHONE_2 = "phone_demo_uk_001"   # +44 7700 900123  (WABA_1)
PHONE_3 = "phone_demo_in_001"   # +91 9876543210   (WABA_2)
PHONE_4 = "phone_demo_br_001"   # +55 11 9876-5432 (WABA_2)

PHONE_MAP = {
    PHONE_1: {"display": "+1 (555) 100-2000", "name": "TechCorp US",        "waba": WABA_1, "country": "US"},
    PHONE_2: {"display": "+44 7700 900123",   "name": "TechCorp UK",        "waba": WABA_1, "country": "GB"},
    PHONE_3: {"display": "+91 98765 43210",   "name": "RetailBrand India",  "waba": WABA_2, "country": "IN"},
    PHONE_4: {"display": "+55 11 9876-5432",  "name": "RetailBrand Brazil", "waba": WABA_2, "country": "BR"},
}

# Contact WA IDs (simulated customers) with country prefixes
CONTACTS = {
    "US": ["14155550101", "13105550202", "12125550303", "16465550404", "18005550505"],
    "GB": ["447911123456", "447922234567", "447933345678"],
    "IN": ["919876543001", "919876543002", "919876543003", "919876543004"],
    "BR": ["5511987650001", "5511987650002", "5511987650003"],
    "DE": ["4915209876001", "4915209876002"],
    "SA": ["966501234001", "966501234002"],
}
ALL_CONTACTS = [c for cs in CONTACTS.values() for c in cs]


# ─── Template definitions ─────────────────────────────────────────────────────

TEMPLATES = [
    # APPROVED - UTILITY
    {"name": "hello_world",         "category": "UTILITY",         "status": "APPROVED", "language": "en_US",
     "body": "Hello {{1}}, welcome to {{2}}! Your account is now active.",
     "header": "Welcome aboard"},
    {"name": "order_shipped",       "category": "UTILITY",         "status": "APPROVED", "language": "en_US",
     "body": "Your order #{{1}} has shipped! Estimated delivery: {{2}}. Track at: {{3}}"},
    {"name": "order_delivered",     "category": "UTILITY",         "status": "APPROVED", "language": "en_US",
     "body": "Great news! Your order #{{1}} has been delivered to {{2}}. Enjoy!"},
    {"name": "appointment_reminder","category": "UTILITY",         "status": "APPROVED", "language": "en_US",
     "body": "Reminder: Your appointment for {{1}} is on {{2}} at {{3}}. Reply CONFIRM to confirm."},
    {"name": "payment_received",    "category": "UTILITY",         "status": "APPROVED", "language": "en_US",
     "body": "Payment of {{1}} {{2}} received successfully for invoice #{{3}}. Thank you!"},
    {"name": "account_activated",   "category": "UTILITY",         "status": "APPROVED", "language": "en_US",
     "body": "Hi {{1}}, your account has been activated. Login at {{2}}"},
    {"name": "ticket_resolved",     "category": "UTILITY",         "status": "APPROVED", "language": "en_US",
     "body": "Your support ticket #{{1}} has been resolved. Rate your experience: {{2}}"},
    {"name": "otp_verify",          "category": "AUTHENTICATION",  "status": "APPROVED", "language": "en_US",
     "body": "Your verification code is *{{1}}*. Valid for 5 minutes. Do not share this code."},
    {"name": "login_alert",         "category": "AUTHENTICATION",  "status": "APPROVED", "language": "en_US",
     "body": "New login to your account from {{1}} at {{2}}. Not you? Secure your account: {{3}}"},
    {"name": "summer_sale",         "category": "MARKETING",       "status": "APPROVED", "language": "en_US",
     "body": "Hi {{1}}! Summer sale is here 🎉 Get {{2}}% off all products. Use code {{3}} at checkout. Valid till {{4}}.",
     "footer": "Reply STOP to unsubscribe"},
    {"name": "product_launch",      "category": "MARKETING",       "status": "APPROVED", "language": "en_US",
     "body": "Exciting news {{1}}! Our new *{{2}}* just launched. Be the first to try it: {{3}}",
     "footer": "Reply STOP to unsubscribe"},
    {"name": "loyalty_reward",      "category": "MARKETING",       "status": "APPROVED", "language": "en_US",
     "body": "Congrats {{1}}! You've earned *{{2}} points*. Redeem them at {{3}} before they expire on {{4}}.",
     "footer": "Reply STOP to unsubscribe"},
    # PENDING
    {"name": "invoice_ready",       "category": "UTILITY",         "status": "PENDING",  "language": "en_US",
     "body": "Your invoice #{{1}} for {{2}} is ready. Download at {{3}}"},
    {"name": "restock_alert",       "category": "MARKETING",       "status": "PENDING",  "language": "en_US",
     "body": "{{1}} is back in stock! Grab yours before it sells out again: {{2}}"},
    # REJECTED
    {"name": "bulk_promo_v1",       "category": "MARKETING",       "status": "REJECTED", "language": "en_US",
     "body": "BUY NOW! Get 70% OFF everything. Limited time only. Click: {{1}}",
     "rejection_reason": "Template uses aggressive promotional language that violates WhatsApp commerce policies"},
    # PAUSED
    {"name": "flash_sale_24h",      "category": "MARKETING",       "status": "PAUSED",   "language": "en_US",
     "body": "24-hour flash sale! {{1}}% off everything. Code: {{2}}. Ends midnight!",
     "footer": "Reply STOP to unsubscribe"},
]

# Which templates get used for outbound messages (only APPROVED)
APPROVED_TEMPLATES = [t for t in TEMPLATES if t["status"] == "APPROVED"]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def rand_ts(days_ago_max=60, days_ago_min=0, business_hours=True):
    """Random ISO timestamp within the last N days."""
    base = datetime.now(timezone.utc)
    delta_days = random.uniform(days_ago_min, days_ago_max)
    dt = base - timedelta(days=delta_days)
    if business_hours:
        # Weight towards 9am-7pm
        hour = random.choices(range(24), weights=[
            1,1,1,1,1,1,1,2,3,5,7,8,8,7,6,6,5,5,4,3,2,2,1,1
        ])[0]
        dt = dt.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))
    return dt.isoformat()


def wamid():
    return f"wamid.HBg{random.randint(100000, 999999)}{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=20))}"


def pick_phone_and_country(waba_filter=None):
    phones = [(pid, info) for pid, info in PHONE_MAP.items() 
              if not waba_filter or info["waba"] == waba_filter]
    pid, info = random.choice(phones)
    # Pick a contact from the phone's country or adjacent
    country = info["country"]
    if country in CONTACTS:
        contact = random.choice(CONTACTS[country])
    else:
        contact = random.choice(ALL_CONTACTS)
    return pid, info["country"], contact


# ─── Main seeder ─────────────────────────────────────────────────────────────

async def seed_demo(db, tenant_id: str):
    print(f"\n🌱 Seeding demo data for tenant {tenant_id}")
    now = datetime.now(timezone.utc).isoformat()

    # ── 1. WABAs ─────────────────────────────────────────────────────────────
    print("  → WABAs...")
    for waba_id, waba_name in [
        (WABA_1, "TechCorp Messaging"),
        (WABA_2, "RetailBrand Alerts"),
    ]:
        wid = str(uuid.uuid4())
        await db.wabas.update_one(
            {"waba_id": waba_id, "tenant_id": tenant_id},
            {"$setOnInsert": {
                "_id": wid, "id": wid,
                "tenant_id": tenant_id,
                "waba_id": waba_id,
                "business_id": f"biz_{waba_id}",
                "name": waba_name,
                "is_demo": True,
                "templates_last_synced_at": now,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(),
            }},
            upsert=True,
        )
        await db.waba_credentials.update_one(
            {"waba_id": waba_id},
            {"$setOnInsert": {
                "_id": f"cred_{waba_id}",
                "waba_id": waba_id,
                "encrypted_business_token": encrypt("DEMO_MOCK_TOKEN_NOT_REAL"),
                "created_at": now, "updated_at": now,
            }},
            upsert=True,
        )

    # ── 2. Phone numbers ─────────────────────────────────────────────────────
    print("  → Phone numbers...")
    for phone_id, info in PHONE_MAP.items():
        pid = str(uuid.uuid4())
        await db.phone_numbers.update_one(
            {"phone_number_id": phone_id, "tenant_id": tenant_id},
            {"$setOnInsert": {
                "_id": pid, "id": pid,
                "tenant_id": tenant_id,
                "waba_id": info["waba"],
                "phone_number_id": phone_id,
                "display_phone_number": info["display"],
                "verified_name": info["name"],
                "quality_rating": random.choice(["GREEN", "GREEN", "GREEN", "YELLOW"]),
                "created_at": (datetime.now(timezone.utc) - timedelta(days=85)).isoformat(),
            }},
            upsert=True,
        )

    # ── 3. Templates ─────────────────────────────────────────────────────────
    print("  → Templates...")
    waba_cycle = [WABA_1, WABA_2, WABA_1, WABA_2]
    for i, tmpl in enumerate(TEMPLATES):
        waba_id = waba_cycle[i % len(waba_cycle)]
        tid = str(uuid.uuid4())
        created = (datetime.now(timezone.utc) - timedelta(days=random.randint(10, 80))).isoformat()
        components = []
        if tmpl.get("header"):
            components.append({"type": "HEADER", "format": "TEXT", "text": tmpl["header"]})
        components.append({"type": "BODY", "text": tmpl["body"]})
        if tmpl.get("footer"):
            components.append({"type": "FOOTER", "text": tmpl["footer"]})

        await db.templates.update_one(
            {"tenant_id": tenant_id, "waba_id": waba_id, "name": tmpl["name"], "language": tmpl["language"]},
            {"$setOnInsert": {
                "_id": tid, "id": tid,
                "tenant_id": tenant_id,
                "waba_id": waba_id,
                "name": tmpl["name"],
                "language": tmpl["language"],
                "category": tmpl["category"],
                "body": tmpl["body"],
                "components": components,
                "status": tmpl["status"],
                "rejection_reason": tmpl.get("rejection_reason"),
                "meta_template_id": f"meta_tpl_{random.randint(100000000, 999999999)}",
                "source": "meta",
                "created_at": created,
                "updated_at": created,
            }},
            upsert=True,
        )

    # ── 4. Messages + Conversations + Usage rollup ────────────────────────────
    print("  → Conversations, messages & usage rollup (this takes a moment)...")

    # Create 30 conversations
    conv_list = []
    for phone_id, info in PHONE_MAP.items():
        country = info["country"]
        contacts = CONTACTS.get(country, ALL_CONTACTS)
        num_convs = random.randint(5, 10)
        for contact_wa_id in random.sample(contacts * 3, min(num_convs, len(contacts * 3))):
            conv_id = f"conv_{phone_id}_{contact_wa_id}"
            last_inbound = rand_ts(days_ago_max=2, days_ago_min=0)
            status = random.choices(["open", "closed"], weights=[70, 30])[0]
            created_dt = datetime.now(timezone.utc) - timedelta(days=random.randint(5, 50))
            await db.conversations.update_one(
                {"id": conv_id, "tenant_id": tenant_id},
                {"$setOnInsert": {
                    "_id": conv_id, "id": conv_id,
                    "tenant_id": tenant_id,
                    "phone_number_id": phone_id,
                    "contact_wa_id": contact_wa_id,
                    "status": status,
                    "assigned_to": None,
                    "unread_count": random.randint(0, 5) if status == "open" else 0,
                    "last_inbound_at": last_inbound,
                    "created_at": created_dt.isoformat(),
                    "updated_at": last_inbound,
                }},
                upsert=True,
            )
            conv_list.append({
                "id": conv_id, "phone_id": phone_id,
                "contact": contact_wa_id, "country": country,
                "waba": info["waba"],
            })

    # ── 5. Messages (300+ spread over 60 days) ────────────────────────────────
    print("  → Messages (300+)...")
    ALL_PHONES = list(PHONE_MAP.keys())

    # Track per-day cost for rollup
    rollup: dict[str, dict] = {}  # key = "tenant:day:category:country"

    def add_rollup(day, category, country, billable, cost):
        key = f"{tenant_id}:{day}:{category}:{country}"
        if key not in rollup:
            rollup[key] = {
                "_id": key, "tenant_id": tenant_id,
                "day": day, "category": category, "country_code": country,
                "delivered_count": 0, "billable_count": 0, "free_count": 0,
                "cost_amount": 0.0, "cost_currency": "USD",
                "updated_at": now,
            }
        rollup[key]["delivered_count"] += 1
        if billable:
            rollup[key]["billable_count"] += 1
            rollup[key]["cost_amount"] += cost
        else:
            rollup[key]["free_count"] += 1

    COST_MAP = {"MARKETING": 0.025, "AUTHENTICATION": 0.015, "UTILITY": 0.015}

    messages_to_insert = []

    for day_offset in range(60):
        day_dt = datetime.now(timezone.utc) - timedelta(days=60 - day_offset)
        day_str = day_dt.date().isoformat()
        is_weekday = day_dt.weekday() < 5
        n_messages = random.randint(6, 18) if is_weekday else random.randint(1, 5)

        for _ in range(n_messages):
            conv = random.choice(conv_list)
            phone_id = conv["phone_id"]
            contact = conv["contact"]
            country = conv["country"]
            waba_id = conv["waba"]
            conv_id = conv["id"]

            hour = random.choices(range(24), weights=[1,1,1,1,1,1,1,2,3,5,7,8,8,7,6,6,5,5,4,3,2,2,1,1])[0]
            created_dt = day_dt.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59), microsecond=0)
            created_iso = created_dt.isoformat()
            month_str = created_dt.strftime("%Y-%m")

            if random.random() < 0.75:
                # Outbound template message
                tmpl = random.choice(APPROVED_TEMPLATES)
                category = tmpl["category"]
                status = random.choices(
                    ["delivered", "read", "failed", "sent"],
                    weights=[50, 35, 3, 12]
                )[0]

                billable = category in ("MARKETING", "AUTHENTICATION") or random.random() < 0.6
                cost = COST_MAP.get(category, 0.015) if billable and status in ("delivered", "read") else 0.0

                mid = str(uuid.uuid4())
                messages_to_insert.append({
                    "_id": mid, "id": mid,
                    "tenant_id": tenant_id,
                    "phone_number_id": phone_id,
                    "conversation_id": conv_id,
                    "direction": "outbound",
                    "msg_type": "template",
                    "to_wa_id": contact,
                    "template_name": tmpl["name"],
                    "status": status,
                    "meta_message_id": wamid(),
                    "pricing_category": category.lower(),
                    "pricing_billable": billable,
                    "cost_amount": round(cost, 4),
                    "country_code": country,
                    "created_at": created_iso,
                    "month": month_str,
                    "sent_at": created_iso,
                    "delivered_at": created_iso if status in ("delivered", "read") else None,
                    "read_at": created_iso if status == "read" else None,
                    "failed_at": created_iso if status == "failed" else None,
                    "error": random.choice([
                        "Message failed to send: Phone number not on WhatsApp",
                        "User blocked business",
                    ]) if status == "failed" else None,
                })

                if status in ("delivered", "read"):
                    add_rollup(day_str, category.lower(), country, billable, cost)

            else:
                # Inbound message
                inbound_bodies = [
                    "Hi, I need help with my order", "Thank you!", "When will it arrive?",
                    "Can I change my delivery address?", "CONFIRM", "YES", "STOP",
                    "Please call me back", "What are your business hours?",
                    "I'm interested in this product", "How much does shipping cost?",
                    "Great service!", "My package is damaged", "I'd like a refund please",
                ]
                mid = str(uuid.uuid4())
                messages_to_insert.append({
                    "_id": mid, "id": mid,
                    "tenant_id": tenant_id,
                    "phone_number_id": phone_id,
                    "conversation_id": conv_id,
                    "direction": "inbound",
                    "msg_type": "text",
                    "from_wa_id": contact,
                    "body": random.choice(inbound_bodies),
                    "status": "delivered",
                    "meta_message_id": wamid(),
                    "created_at": created_iso,
                    "month": month_str,
                    "country_code": country,
                })

    # Bulk insert messages (skip if _id already exists)
    if messages_to_insert:
        try:
            await db.messages.insert_many(messages_to_insert, ordered=False)
            print(f"     Inserted {len(messages_to_insert)} messages")
        except Exception as e:
            # Some duplicates expected on re-run - that's ok
            pass

    # ── 6. Usage daily rollup ─────────────────────────────────────────────────
    print("  → Usage daily rollup...")
    rollup_docs = []
    for r in rollup.values():
        r["cost_amount"] = round(r["cost_amount"], 4)
        rollup_docs.append(r)

    if rollup_docs:
        for doc in rollup_docs:
            await db.usage_daily_rollup.update_one(
                {"_id": doc["_id"]},
                {"$setOnInsert": doc},
                upsert=True,
            )
        print(f"     Inserted/updated {len(rollup_docs)} rollup rows")

    # ── 7. Template performance rollup ───────────────────────────────────────
    print("  → Template performance rollup...")
    tpl_perf: dict[str, dict] = {}
    async for msg in db.messages.find({"tenant_id": tenant_id, "direction": "outbound", "template_name": {"$ne": None}}):
        tmpl_name = msg.get("template_name")
        month = msg.get("month") or msg.get("created_at", "")[:7]
        key = f"{tenant_id}:{tmpl_name}:{month}"
        if key not in tpl_perf:
            tpl_perf[key] = {
                "_id": key, "tenant_id": tenant_id,
                "template_name": tmpl_name, "month": month,
                "sent": 0, "delivered": 0, "read": 0, "failed": 0,
            }
        tpl_perf[key]["sent"] += 1
        status = msg.get("status")
        if status in ("delivered", "read"): tpl_perf[key]["delivered"] += 1
        if status == "read": tpl_perf[key]["read"] += 1
        if status == "failed": tpl_perf[key]["failed"] += 1

    for doc in tpl_perf.values():
        await db.template_perf_rollup.update_one(
            {"_id": doc["_id"]},
            {"$setOnInsert": doc},
            upsert=True,
        )
    print(f"     Inserted {len(tpl_perf)} template perf rows")

    # ── 8. Audit log entries ─────────────────────────────────────────────────
    print("  → Audit log entries...")
    audit_entries = [
        {"action": "message.send", "metadata": {"template": "order_shipped", "to": "14155550101"}},
        {"action": "message.send", "metadata": {"template": "otp_verify", "to": "447911123456"}},
        {"action": "message.send", "metadata": {"template": "summer_sale", "to": "919876543001"}},
        {"action": "onboarding.waba_connected", "metadata": {"waba_id": WABA_1}},
        {"action": "onboarding.waba_connected", "metadata": {"waba_id": WABA_2}},
        {"action": "template.sync", "metadata": {"waba_id": WABA_1, "synced": 8}},
        {"action": "template.sync", "metadata": {"waba_id": WABA_2, "synced": 7}},
    ]
    # Get the demo user id
    user = await db.users.find_one({"email": "owner@demo.com"})
    actor_id = user["_id"] if user else "unknown"
    for entry in audit_entries:
        eid = str(uuid.uuid4())
        created = rand_ts(days_ago_max=30)
        await db.audit_log.insert_one({
            "_id": eid, "tenant_id": tenant_id,
            "actor_user_id": actor_id,
            "action": entry["action"],
            "metadata": entry["metadata"],
            "created_at": created,
        })
    print(f"     Inserted {len(audit_entries)} audit entries")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n✅ Demo seed complete!")
    print(f"   WABAs:        {await db.wabas.count_documents({'tenant_id': tenant_id})}")
    print(f"   Phones:       {await db.phone_numbers.count_documents({'tenant_id': tenant_id})}")
    print(f"   Templates:    {await db.templates.count_documents({'tenant_id': tenant_id})}")
    print(f"   Messages:     {await db.messages.count_documents({'tenant_id': tenant_id})}")
    print(f"   Conversations:{await db.conversations.count_documents({'tenant_id': tenant_id})}")
    print(f"   Rollup rows:  {await db.usage_daily_rollup.count_documents({'tenant_id': tenant_id})}")


async def main():
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.DB_NAME]
    tenant = await db.tenants.find_one({"name": "Demo Inc"})
    if not tenant:
        print("❌ Demo tenant not found — run the backend once first to seed it")
        return
    await seed_demo(db, tenant["_id"])
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
