"""
OT Sentinel — DynamoDB seed script.

Usage:
    python scripts/seed-data.py

Environment variables (all optional, defaults match config.py):
    DYNAMODB_ENDPOINT_URL   — set to http://localhost:8001 for DynamoDB Local
    USERS_TABLE             — default: otsentinel-prod-users
    DEVICES_TABLE           — default: otsentinel-prod-devices
    INCIDENTS_TABLE         — default: otsentinel-prod-incidents
    AUDIT_TABLE             — default: otsentinel-prod-audit
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import boto3

# ── Configuration ─────────────────────────────────────────────────────────────

ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT_URL")
REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-1")

USERS_TABLE = os.environ.get("USERS_TABLE", "otsentinel-prod-users")
DEVICES_TABLE = os.environ.get("DEVICES_TABLE", "otsentinel-prod-devices")
INCIDENTS_TABLE = os.environ.get("INCIDENTS_TABLE", "otsentinel-prod-incidents")
AUDIT_TABLE = os.environ.get("AUDIT_TABLE", "otsentinel-prod-audit")


def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# ── DynamoDB client factory ────────────────────────────────────────────────────

def get_dynamo_client():
    kwargs = {"region_name": REGION}
    if ENDPOINT:
        kwargs["endpoint_url"] = ENDPOINT
        kwargs["aws_access_key_id"] = "local"
        kwargs["aws_secret_access_key"] = "local"
        print(f"  Using local DynamoDB at {ENDPOINT}")
    else:
        print(f"  Using AWS DynamoDB in region {REGION}")
    return boto3.client("dynamodb", **kwargs)


def get_dynamo_resource():
    kwargs = {"region_name": REGION}
    if ENDPOINT:
        kwargs["endpoint_url"] = ENDPOINT
        kwargs["aws_access_key_id"] = "local"
        kwargs["aws_secret_access_key"] = "local"
    return boto3.resource("dynamodb", **kwargs)


# ── Table creation ─────────────────────────────────────────────────────────────

def create_tables(client):
    print("\n[1] Creating tables if they don't exist...")

    tables = {
        USERS_TABLE: {
            "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "email", "AttributeType": "S"},
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "email-index",
                    "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        },
        DEVICES_TABLE: {
            "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
                {"AttributeName": "last_seen", "AttributeType": "S"},
                {"AttributeName": "site_id", "AttributeType": "S"},
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "status-index",
                    "KeySchema": [
                        {"AttributeName": "status", "KeyType": "HASH"},
                        {"AttributeName": "last_seen", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "site-index",
                    "KeySchema": [
                        {"AttributeName": "site_id", "KeyType": "HASH"},
                        {"AttributeName": "PK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        },
        INCIDENTS_TABLE: {
            "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "device_id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "S"},
                {"AttributeName": "severity", "AttributeType": "S"},
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "device-index",
                    "KeySchema": [
                        {"AttributeName": "device_id", "KeyType": "HASH"},
                        {"AttributeName": "created_at", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "severity-index",
                    "KeySchema": [
                        {"AttributeName": "severity", "KeyType": "HASH"},
                        {"AttributeName": "created_at", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        },
        AUDIT_TABLE: {
            "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "user-index",
                    "KeySchema": [
                        {"AttributeName": "user_id", "KeyType": "HASH"},
                        {"AttributeName": "timestamp", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        },
    }

    for table_name, schema in tables.items():
        try:
            client.create_table(
                TableName=table_name,
                KeySchema=schema["KeySchema"],
                AttributeDefinitions=schema["AttributeDefinitions"],
                BillingMode="PAY_PER_REQUEST",
                GlobalSecondaryIndexes=schema["GlobalSecondaryIndexes"],
            )
            print(f"  Created: {table_name}")
        except client.exceptions.ResourceInUseException:
            print(f"  Already exists: {table_name}")
        except Exception as e:
            print(f"  Error creating {table_name}: {e}", file=sys.stderr)


# ── Seed users ─────────────────────────────────────────────────────────────────

def seed_users(resource):
    print("\n[2] Seeding users...")
    table = resource.Table(USERS_TABLE)

    users = [
        {
            "user_id": str(uuid.uuid4()),
            "email": "admin@otsentinel.com",
            "password": "Admin1234!",
            "role": "admin",
            "name": "Admin User",
        },
        {
            "user_id": str(uuid.uuid4()),
            "email": "operator@otsentinel.com",
            "password": "Oper1234!",
            "role": "operator",
            "name": "Ops Engineer",
        },
    ]

    created_users = []
    for u in users:
        # Check if user already exists
        resp = table.query(
            IndexName="email-index",
            KeyConditionExpression="email = :e",
            ExpressionAttributeValues={":e": u["email"]},
        )
        if resp.get("Items"):
            print(f"  WARNING: User {u['email']} already exists, skipping.")
            created_users.append(resp["Items"][0])
            continue

        item = {
            "PK": f"USER#{u['user_id']}",
            "user_id": u["user_id"],
            "email": u["email"],
            "password_hash": _hash_password(u["password"]),
            "role": u["role"],
            "name": u["name"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        table.put_item(Item=item)
        created_users.append(item)
        print(f"  Created user: {u['email']} (role={u['role']})")

    return created_users


# ── Table purge helpers ────────────────────────────────────────────────────────

def _purge_table(table):
    """Delete all items from a DynamoDB table using scan + batch_writer."""
    key_names = [s["AttributeName"] for s in table.key_schema]
    scan_kwargs = {}
    deleted = 0
    while True:
        resp = table.scan(**scan_kwargs)
        items = resp.get("Items", [])
        if items:
            with table.batch_writer() as batch:
                for item in items:
                    key = {k: item[k] for k in key_names}
                    batch.delete_item(Key=key)
            deleted += len(items)
        last = resp.get("LastEvaluatedKey")
        if not last:
            break
        scan_kwargs["ExclusiveStartKey"] = last
    return deleted


# ── Seed devices ───────────────────────────────────────────────────────────────

def seed_devices(resource):
    print("\n[3] Seeding devices...")
    table = resource.Table(DEVICES_TABLE)

    deleted = _purge_table(table)
    if deleted:
        print(f"  Deleted {deleted} existing device(s).")

    now = datetime.now(timezone.utc)

    # Fab 18 — Tainan  /  single-fab bay-level layout
    devices_data = [
        # Bay 1 — Lithography Bay
        {"name": "EUV-Scanner-01",   "type": "PLC",     "bay_id": "bay1",   "bay_name": "Lithography Bay",
         "status": "online",   "ip": "10.1.1.11", "firmware": "EUV-FW-4.2.1",  "risk_score": 72, "last_seen_offset_minutes": 1},
        {"name": "ArF-Immersion-01", "type": "PLC",     "bay_id": "bay1",   "bay_name": "Lithography Bay",
         "status": "online",   "ip": "10.1.1.12", "firmware": "ArF-FW-3.8.0",  "risk_score": 65, "last_seen_offset_minutes": 2},
        # Bay 2 — Thin Film Bay
        {"name": "CVD-Chamber-A",    "type": "PLC",     "bay_id": "bay2",   "bay_name": "Thin Film Bay",
         "status": "warning",  "ip": "10.2.1.11", "firmware": "CVD-FW-2.5.3",  "risk_score": 61, "last_seen_offset_minutes": 10},
        {"name": "ALD-System-01",    "type": "RTU",     "bay_id": "bay2",   "bay_name": "Thin Film Bay",
         "status": "online",   "ip": "10.2.1.12", "firmware": "ALD-FW-1.9.7",  "risk_score": 45, "last_seen_offset_minutes": 3},
        {"name": "PECVD-Chamber-B",  "type": "PLC",     "bay_id": "bay2",   "bay_name": "Thin Film Bay",
         "status": "online",   "ip": "10.2.1.13", "firmware": "PECVD-FW-2.1.0","risk_score": 38, "last_seen_offset_minutes": 4},
        # Bay 3 — Etch Bay
        {"name": "Dry-Etch-01",      "type": "RTU",     "bay_id": "bay3",   "bay_name": "Etch Bay",
         "status": "online",   "ip": "10.3.1.11", "firmware": "ETCH-FW-3.3.2", "risk_score": 42, "last_seen_offset_minutes": 2},
        {"name": "Dry-Etch-02",      "type": "RTU",     "bay_id": "bay3",   "bay_name": "Etch Bay",
         "status": "critical", "ip": "10.3.1.12", "firmware": "ETCH-FW-3.3.2", "risk_score": 88, "last_seen_offset_minutes": 30},
        # Sub-Fab Utilities
        {"name": "Chiller-Main",     "type": "Gateway", "bay_id": "subfab", "bay_name": "Sub-Fab Utilities",
         "status": "online",   "ip": "10.0.1.11", "firmware": "CHILL-FW-1.4.0","risk_score": 30, "last_seen_offset_minutes": 1},
        {"name": "UPW-System-01",    "type": "Gateway", "bay_id": "subfab", "bay_name": "Sub-Fab Utilities",
         "status": "online",   "ip": "10.0.1.12", "firmware": "UPW-FW-2.0.1",  "risk_score": 28, "last_seen_offset_minutes": 1},
        {"name": "N2-Gas-Supply",    "type": "Sensor",  "bay_id": "subfab", "bay_name": "Sub-Fab Utilities",
         "status": "warning",  "ip": "10.0.1.13", "firmware": "GAS-FW-1.1.5",  "risk_score": 55, "last_seen_offset_minutes": 20},
    ]

    created_devices = []
    for d in devices_data:
        device_id = str(uuid.uuid4())
        last_seen = (now - timedelta(minutes=d["last_seen_offset_minutes"])).isoformat()
        item = {
            "PK": f"DEVICE#{device_id}",
            "device_id": device_id,
            "name": d["name"],
            "type": d["type"],
            "site_id": "fab18",
            "site_name": "Fab 18 — Tainan",
            "bay_id": d["bay_id"],
            "bay_name": d["bay_name"],
            "status": d["status"],
            "ip_address": d["ip"],
            "firmware_version": d["firmware"],
            "last_seen": last_seen,
            "risk_score": d["risk_score"],
        }
        table.put_item(Item=item)
        created_devices.append(item)
        print(f"  Created device: {d['name']} ({d['type']}, {d['status']}, {d['bay_id']})")

    return created_devices


# ── Seed incidents ─────────────────────────────────────────────────────────────

def seed_incidents(resource, devices):
    print("\n[4] Seeding incidents...")
    table = resource.Table(INCIDENTS_TABLE)

    deleted = _purge_table(table)
    if deleted:
        print(f"  Deleted {deleted} existing incident(s).")

    now = datetime.now(timezone.utc)

    # Build name -> (device_id, name) lookup for deterministic assignment
    device_by_name = {d["name"]: (d["device_id"], d["name"]) for d in devices}
    device_pool = list(device_by_name.values())

    def _dev(name):
        return device_by_name.get(name, device_pool[0])

    incidents_data = [
        # EUV-Scanner-01 (risk 72, online)
        {"device": "EUV-Scanner-01", "title": "EUV source power fluctuation detected",
         "severity": "high", "status": "investigating",
         "description": "EUV plasma source output dropped 18% below set-point; dose uniformity at risk.",
         "risk_score": 74, "days_ago": 0},
        # ArF-Immersion-01 (risk 65, online)
        {"device": "ArF-Immersion-01", "title": "Immersion hood leak — water contamination alert",
         "severity": "critical", "status": "open",
         "description": "Fluid sensor detected trace DI water ingress near wafer stage; process suspended.",
         "risk_score": 91, "days_ago": 0},
        # CVD-Chamber-A (risk 61, warning)
        {"device": "CVD-Chamber-A", "title": "CVD precursor flow rate out of spec",
         "severity": "high", "status": "open",
         "description": "MFC reading for TEOS precursor is 12% above recipe limit; film thickness deviation expected.",
         "risk_score": 67, "days_ago": 1},
        # CVD-Chamber-A second incident
        {"device": "CVD-Chamber-A", "title": "Unauthorized recipe parameter change",
         "severity": "critical", "status": "open",
         "description": "CVD process recipe modified outside change-control window by unrecognized user session.",
         "risk_score": 95, "days_ago": 0},
        # ALD-System-01 (risk 45, online)
        {"device": "ALD-System-01", "title": "ALD cycle count mismatch",
         "severity": "medium", "status": "open",
         "description": "Reported cycle count diverges from expected value by 3 cycles; potential underfill.",
         "risk_score": 48, "days_ago": 2},
        # PECVD-Chamber-B (risk 38, online)
        {"device": "PECVD-Chamber-B", "title": "RF power matching network alarm",
         "severity": "medium", "status": "investigating",
         "description": "Impedance mismatch on 13.56 MHz RF network causing reflected power spikes.",
         "risk_score": 41, "days_ago": 1},
        # Dry-Etch-01 (risk 42, online)
        {"device": "Dry-Etch-01", "title": "Etch endpoint detection timeout",
         "severity": "medium", "status": "resolved",
         "description": "OES endpoint signal did not clear within defined window; lot held for metrology review.",
         "risk_score": 44, "days_ago": 3},
        # Dry-Etch-02 (risk 88, critical)
        {"device": "Dry-Etch-02", "title": "Dry etch chamber pressure spike — process abort",
         "severity": "critical", "status": "open",
         "description": "Chamber pressure jumped to 850 mTorr during over-etch step; automatic safety interlock triggered.",
         "risk_score": 92, "days_ago": 0},
        {"device": "Dry-Etch-02", "title": "Anomalous Modbus write to etch PLC",
         "severity": "critical", "status": "investigating",
         "description": "Non-standard Modbus FC 16 command with unknown register range observed on OT network segment.",
         "risk_score": 97, "days_ago": 0},
        # Dry-Etch-02 third incident
        {"device": "Dry-Etch-02", "title": "Etch rate drift — CD uniformity degraded",
         "severity": "high", "status": "investigating",
         "description": "In-situ etch rate dropped 9% over last 8 wafers; critical dimension uniformity out of spec.",
         "risk_score": 80, "days_ago": 1},
        # Chiller-Main (risk 30, online)
        {"device": "Chiller-Main", "title": "Chiller coolant temperature above set-point",
         "severity": "low", "status": "resolved",
         "description": "Chiller outlet temperature drifted +1.2 °C above set-point; process tools self-corrected.",
         "risk_score": 22, "days_ago": 4},
        # UPW-System-01 (risk 28, online)
        {"device": "UPW-System-01", "title": "UPW resistivity drop detected",
         "severity": "medium", "status": "resolved",
         "description": "UPW resistivity fell to 17.8 MΩ·cm (threshold 18.2); DI polisher regeneration triggered.",
         "risk_score": 35, "days_ago": 5},
        # N2-Gas-Supply (risk 55, warning)
        {"device": "N2-Gas-Supply", "title": "N2 supply pressure below minimum threshold",
         "severity": "high", "status": "open",
         "description": "Nitrogen header pressure reading 5.8 bar; minimum for fab operations is 6.0 bar.",
         "risk_score": 72, "days_ago": 0},
        # EUV-Scanner-01 second incident
        {"device": "EUV-Scanner-01", "title": "Reticle stage position error",
         "severity": "medium", "status": "resolved",
         "description": "Reticle stage reported 15 nm position error outside overlay budget during PM validation.",
         "risk_score": 50, "days_ago": 6},
        # ALD-System-01 second incident
        {"device": "ALD-System-01", "title": "Precursor valve firmware version mismatch",
         "severity": "low", "status": "resolved",
         "description": "ALD precursor valve controller firmware does not match approved baseline v1.9.7.",
         "risk_score": 18, "days_ago": 7},
    ]

    for inc in incidents_data:
        incident_id = str(uuid.uuid4())
        device_id, device_name = _dev(inc["device"])
        created_at = (now - timedelta(days=inc["days_ago"])).isoformat()
        resolved_at = None
        if inc["status"] == "resolved":
            resolved_at = (now - timedelta(days=max(0, inc["days_ago"] - 1))).isoformat()

        item = {
            "PK": f"INCIDENT#{incident_id}",
            "incident_id": incident_id,
            "device_id": device_id,
            "device_name": device_name,
            "severity": inc["severity"],
            "status": inc["status"],
            "title": inc["title"],
            "description": inc["description"],
            "risk_score": inc["risk_score"],
            "created_at": created_at,
        }
        if resolved_at:
            item["resolved_at"] = resolved_at

        table.put_item(Item=item)
        print(f"  Created incident: [{inc['severity'].upper()}] {inc['title']}")


# ── Seed audit logs ────────────────────────────────────────────────────────────

def seed_audit_logs(resource, users):
    print("\n[5] Seeding audit logs...")
    table = resource.Table(AUDIT_TABLE)

    deleted = _purge_table(table)
    if deleted:
        print(f"  Deleted {deleted} existing audit log(s).")

    now = datetime.now(timezone.utc)

    admin_user = next((u for u in users if u.get("role") == "admin"), users[0])
    operator_user = next((u for u in users if u.get("role") == "operator"), users[-1])

    audit_entries = [
        {"user": admin_user, "action": "LOGIN", "resource_type": "AUTH",
         "resource_id": "session-1", "detail": "Admin user logged in", "ip": "203.0.113.10", "hours_ago": 0.1},
        {"user": operator_user, "action": "LOGIN", "resource_type": "AUTH",
         "resource_id": "session-2", "detail": "Operator user logged in", "ip": "203.0.113.20", "hours_ago": 0.5},
        {"user": admin_user, "action": "VIEW_DEVICE", "resource_type": "DEVICE",
         "resource_id": "device-plc001", "detail": "Viewed PLC-001 device details", "ip": "203.0.113.10", "hours_ago": 1},
        {"user": operator_user, "action": "VIEW_INCIDENT", "resource_type": "INCIDENT",
         "resource_id": "incident-001", "detail": "Viewed critical incident: Unauthorized access attempt", "ip": "203.0.113.20", "hours_ago": 1.5},
        {"user": admin_user, "action": "ACKNOWLEDGE_INCIDENT", "resource_type": "INCIDENT",
         "resource_id": "incident-002", "detail": "Acknowledged high severity incident", "ip": "203.0.113.10", "hours_ago": 2},
        {"user": operator_user, "action": "VIEW_DEVICE", "resource_type": "DEVICE",
         "resource_id": "device-hmi002", "detail": "Viewed HMI-Floor2 device details", "ip": "203.0.113.20", "hours_ago": 2.5},
        {"user": admin_user, "action": "UPDATE_DEVICE", "resource_type": "DEVICE",
         "resource_id": "device-rtu003", "detail": "Updated RTU-Pump3 risk score", "ip": "203.0.113.10", "hours_ago": 3},
        {"user": operator_user, "action": "VIEW_INCIDENT", "resource_type": "INCIDENT",
         "resource_id": "incident-003", "detail": "Viewed medium incident: Firmware version mismatch", "ip": "203.0.113.20", "hours_ago": 4},
        {"user": admin_user, "action": "VIEW_DEVICE", "resource_type": "DEVICE",
         "resource_id": "device-sensor004", "detail": "Viewed Sensor-Temp4 device details", "ip": "203.0.113.10", "hours_ago": 4.5},
        {"user": operator_user, "action": "ACKNOWLEDGE_INCIDENT", "resource_type": "INCIDENT",
         "resource_id": "incident-004", "detail": "Operator acknowledged communication timeout", "ip": "203.0.113.20", "hours_ago": 5},
        {"user": admin_user, "action": "LOGIN", "resource_type": "AUTH",
         "resource_id": "session-3", "detail": "Admin user logged in from new location", "ip": "198.51.100.5", "hours_ago": 6},
        {"user": operator_user, "action": "VIEW_DEVICE", "resource_type": "DEVICE",
         "resource_id": "device-gw005", "detail": "Viewed Gateway-Main device details", "ip": "203.0.113.20", "hours_ago": 7},
        {"user": admin_user, "action": "UPDATE_DEVICE", "resource_type": "DEVICE",
         "resource_id": "device-plc006", "detail": "Updated PLC-002 firmware metadata", "ip": "203.0.113.10", "hours_ago": 8},
        {"user": operator_user, "action": "VIEW_INCIDENT", "resource_type": "INCIDENT",
         "resource_id": "incident-005", "detail": "Viewed critical incident: Protocol anomaly detected", "ip": "203.0.113.20", "hours_ago": 9},
        {"user": admin_user, "action": "ACKNOWLEDGE_INCIDENT", "resource_type": "INCIDENT",
         "resource_id": "incident-006", "detail": "Admin acknowledged unusual network traffic alert", "ip": "203.0.113.10", "hours_ago": 10},
        {"user": operator_user, "action": "LOGOUT", "resource_type": "AUTH",
         "resource_id": "session-2", "detail": "Operator user logged out", "ip": "203.0.113.20", "hours_ago": 11},
        {"user": admin_user, "action": "VIEW_DEVICE", "resource_type": "DEVICE",
         "resource_id": "device-rtu007", "detail": "Viewed RTU-Valve6 critical device", "ip": "203.0.113.10", "hours_ago": 12},
        {"user": operator_user, "action": "LOGIN", "resource_type": "AUTH",
         "resource_id": "session-4", "detail": "Operator user logged in", "ip": "203.0.113.20", "hours_ago": 16},
        {"user": admin_user, "action": "UPDATE_DEVICE", "resource_type": "DEVICE",
         "resource_id": "device-hmi008", "detail": "Updated HMI-Control7 status to offline", "ip": "203.0.113.10", "hours_ago": 20},
        {"user": operator_user, "action": "VIEW_INCIDENT", "resource_type": "INCIDENT",
         "resource_id": "incident-011", "detail": "Viewed critical incident: PLC ladder logic modified", "ip": "203.0.113.20", "hours_ago": 23},
    ]

    for entry in audit_entries:
        log_id = str(uuid.uuid4())
        timestamp = (now - timedelta(hours=entry["hours_ago"])).isoformat()
        user = entry["user"]
        item = {
            "PK": f"LOG#{log_id}",
            "log_id": log_id,
            "user_id": user.get("user_id", "unknown"),
            "user_email": user.get("email", "unknown"),
            "action": entry["action"],
            "resource_type": entry["resource_type"],
            "resource_id": entry["resource_id"],
            "detail": entry["detail"],
            "ip_address": entry["ip"],
            "timestamp": timestamp,
        }
        table.put_item(Item=item)
        print(f"  Created audit log: [{entry['action']}] {entry['detail'][:50]}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("OT Sentinel — Database Seed Script")
    print("=" * 60)

    client = get_dynamo_client()
    resource = get_dynamo_resource()

    create_tables(client)
    users = seed_users(resource)
    devices = seed_devices(resource)
    seed_incidents(resource, devices)
    seed_audit_logs(resource, users)

    print("\n" + "=" * 60)
    print("Seed complete!")
    print("\nTest credentials:")
    print("  admin@otsentinel.com   / Admin1234!")
    print("  operator@otsentinel.com / Oper1234!")
    print("=" * 60)


if __name__ == "__main__":
    main()
