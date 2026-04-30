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


# ── Seed devices ───────────────────────────────────────────────────────────────

def seed_devices(resource):
    print("\n[3] Seeding devices...")
    table = resource.Table(DEVICES_TABLE)

    # Check if devices already exist
    resp = table.scan(Limit=1)
    if resp.get("Items"):
        print("  WARNING: Devices already exist, skipping seed.")
        resp_all = table.scan()
        return resp_all.get("Items", [])

    now = datetime.now(timezone.utc)

    devices_data = [
        {"name": "PLC-001", "type": "PLC", "site_id": "site-a", "site_name": "Site Alpha",
         "status": "online", "ip": "192.168.10.1", "firmware": "v2.1.0", "risk_score": 15,
         "last_seen_offset_minutes": 2},
        {"name": "HMI-Floor2", "type": "HMI", "site_id": "site-a", "site_name": "Site Alpha",
         "status": "online", "ip": "192.168.10.2", "firmware": "v3.0.1", "risk_score": 8,
         "last_seen_offset_minutes": 5},
        {"name": "RTU-Pump3", "type": "RTU", "site_id": "site-b", "site_name": "Site Beta",
         "status": "warning", "ip": "192.168.10.3", "firmware": "v1.5.3", "risk_score": 55,
         "last_seen_offset_minutes": 15},
        {"name": "Sensor-Temp4", "type": "Sensor", "site_id": "site-b", "site_name": "Site Beta",
         "status": "online", "ip": "192.168.10.4", "firmware": "v2.8.0", "risk_score": 12,
         "last_seen_offset_minutes": 1},
        {"name": "Gateway-Main", "type": "Gateway", "site_id": "site-a", "site_name": "Site Alpha",
         "status": "online", "ip": "192.168.10.5", "firmware": "v3.2.1", "risk_score": 20,
         "last_seen_offset_minutes": 3},
        {"name": "PLC-002", "type": "PLC", "site_id": "site-c", "site_name": "Site Gamma",
         "status": "online", "ip": "192.168.10.6", "firmware": "v2.1.0", "risk_score": 18,
         "last_seen_offset_minutes": 8},
        {"name": "RTU-Valve6", "type": "RTU", "site_id": "site-c", "site_name": "Site Gamma",
         "status": "critical", "ip": "192.168.10.7", "firmware": "v1.5.3", "risk_score": 88,
         "last_seen_offset_minutes": 45},
        {"name": "HMI-Control7", "type": "HMI", "site_id": "site-b", "site_name": "Site Beta",
         "status": "offline", "ip": "192.168.10.8", "firmware": "v3.0.1", "risk_score": 0,
         "last_seen_offset_minutes": 1440},
        {"name": "Sensor-Press8", "type": "Sensor", "site_id": "site-a", "site_name": "Site Alpha",
         "status": "online", "ip": "192.168.10.9", "firmware": "v2.8.0", "risk_score": 22,
         "last_seen_offset_minutes": 4},
        {"name": "Gateway-Backup", "type": "Gateway", "site_id": "site-c", "site_name": "Site Gamma",
         "status": "warning", "ip": "192.168.10.10", "firmware": "v3.2.1", "risk_score": 47,
         "last_seen_offset_minutes": 120},
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
            "site_id": d["site_id"],
            "site_name": d["site_name"],
            "status": d["status"],
            "ip_address": d["ip"],
            "firmware_version": d["firmware"],
            "last_seen": last_seen,
            "risk_score": d["risk_score"],
        }
        table.put_item(Item=item)
        created_devices.append(item)
        print(f"  Created device: {d['name']} ({d['type']}, {d['status']})")

    return created_devices


# ── Seed incidents ─────────────────────────────────────────────────────────────

def seed_incidents(resource, devices):
    print("\n[4] Seeding incidents...")
    table = resource.Table(INCIDENTS_TABLE)

    # Check if incidents already exist
    resp = table.scan(Limit=1)
    if resp.get("Items"):
        print("  WARNING: Incidents already exist, skipping seed.")
        return

    now = datetime.now(timezone.utc)

    # Get device IDs and names for linking
    device_pool = [(d["device_id"], d["name"]) for d in devices[:10]]

    incidents_data = [
        {"title": "Unauthorized access attempt", "severity": "critical", "status": "open",
         "description": "Multiple failed authentication attempts detected from unknown IP address.",
         "risk_score": 92, "days_ago": 0},
        {"title": "Abnormal temperature spike", "severity": "high", "status": "investigating",
         "description": "Temperature sensor reporting values 40% above normal operating range.",
         "risk_score": 71, "days_ago": 1},
        {"title": "Firmware version mismatch", "severity": "medium", "status": "open",
         "description": "Device firmware version does not match approved baseline configuration.",
         "risk_score": 45, "days_ago": 2},
        {"title": "Communication timeout", "severity": "low", "status": "resolved",
         "description": "Periodic communication timeouts detected on primary network interface.",
         "risk_score": 18, "days_ago": 3},
        {"title": "Protocol anomaly detected", "severity": "critical", "status": "open",
         "description": "Non-standard Modbus commands observed on industrial control network.",
         "risk_score": 95, "days_ago": 0},
        {"title": "Unusual network traffic", "severity": "high", "status": "open",
         "description": "Device initiating outbound connections to unrecognized external hosts.",
         "risk_score": 78, "days_ago": 1},
        {"title": "Device configuration changed", "severity": "high", "status": "investigating",
         "description": "PLC configuration parameters modified outside of scheduled maintenance window.",
         "risk_score": 82, "days_ago": 2},
        {"title": "Multiple login failures", "severity": "medium", "status": "resolved",
         "description": "10 consecutive failed login attempts recorded within 60-second window.",
         "risk_score": 50, "days_ago": 4},
        {"title": "Memory overflow warning", "severity": "medium", "status": "open",
         "description": "Device memory utilization exceeded 90% threshold for extended period.",
         "risk_score": 42, "days_ago": 1},
        {"title": "Unexpected device reboot", "severity": "high", "status": "investigating",
         "description": "Device rebooted unexpectedly during active production cycle.",
         "risk_score": 68, "days_ago": 0},
        {"title": "PLC ladder logic modified", "severity": "critical", "status": "open",
         "description": "Unauthorized modification of PLC ladder logic program detected.",
         "risk_score": 98, "days_ago": 0},
        {"title": "HMI display tampering", "severity": "medium", "status": "resolved",
         "description": "Suspicious modifications to HMI display configuration detected.",
         "risk_score": 38, "days_ago": 5},
        {"title": "Network scan detected", "severity": "low", "status": "resolved",
         "description": "Port scan originating from within OT network segment detected.",
         "risk_score": 22, "days_ago": 6},
        {"title": "Sensor data manipulation", "severity": "critical", "status": "investigating",
         "description": "Sensor readings show signs of spoofing or signal injection attack.",
         "risk_score": 90, "days_ago": 0},
        {"title": "VPN tunnel disruption", "severity": "low", "status": "resolved",
         "description": "Intermittent VPN tunnel drops causing brief connectivity gaps.",
         "risk_score": 15, "days_ago": 7},
    ]

    for idx, inc in enumerate(incidents_data):
        incident_id = str(uuid.uuid4())
        device_id, device_name = device_pool[idx % len(device_pool)]
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

    # Check if audit logs already exist
    resp = table.scan(Limit=1)
    if resp.get("Items"):
        print("  WARNING: Audit logs already exist, skipping seed.")
        return

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
