import random
from typing import Tuple

# Anomaly types with (base_min, base_max, title_template, description_template)
ANOMALY_TYPES = {
    "unauthorized_access": (82, 96, "Unauthorized access attempt", "Unauthorized login attempt detected on {device_name}. Multiple failed authentication events recorded."),
    "firmware_tamper": (78, 92, "Firmware tampering detected", "Unexpected firmware modification detected on {device_name}. Version hash mismatch confirmed."),
    "protocol_anomaly": (68, 84, "Protocol anomaly detected", "Non-standard protocol behavior observed on {device_name}. Possible command injection attempt."),
    "config_change": (62, 78, "Unauthorized configuration change", "Device configuration modified on {device_name} outside of maintenance window."),
    "brute_force": (72, 88, "Brute force attack detected", "Multiple failed login attempts on {device_name} from external IP. Possible credential stuffing."),
    "network_scan": (55, 72, "Network scan detected", "Port scanning activity detected targeting {device_name}. Possible reconnaissance activity."),
    "comm_timeout": (35, 52, "Communication timeout", "Repeated communication timeouts on {device_name}. Possible network disruption or DoS."),
    "memory_overflow": (42, 58, "Memory overflow warning", "Memory buffer overflow detected on {device_name}. May indicate exploitation attempt."),
    "unusual_traffic": (52, 68, "Unusual network traffic", "Anomalous outbound traffic pattern from {device_name}. Possible data exfiltration."),
    "sensor_manipulation": (78, 94, "Sensor data manipulation", "Sensor readings from {device_name} show impossible values. Possible spoofing attack."),
}

# Device type risk multipliers
DEVICE_MULTIPLIERS = {
    "PLC": 1.20,
    "RTU": 1.15,
    "HMI": 1.10,
    "Gateway": 1.05,
    "Sensor": 1.00,
}

def calculate_risk(anomaly_type: str, device_type: str) -> Tuple[int, str, str, str]:
    """
    Returns (risk_score, severity, title, description)
    """
    if anomaly_type not in ANOMALY_TYPES:
        raise ValueError(f"Unknown anomaly type: {anomaly_type}")

    base_min, base_max, title_tmpl, desc_tmpl = ANOMALY_TYPES[anomaly_type]
    multiplier = DEVICE_MULTIPLIERS.get(device_type, 1.0)

    base_score = random.randint(base_min, base_max)
    risk_score = min(100, int(base_score * multiplier))

    if risk_score >= 80:
        severity = "critical"
    elif risk_score >= 60:
        severity = "high"
    elif risk_score >= 40:
        severity = "medium"
    else:
        severity = "low"

    return risk_score, severity, title_tmpl, desc_tmpl

def get_anomaly_types() -> list[dict]:
    """Return list of available anomaly types for frontend dropdown."""
    return [
        {"value": k, "label": v[2]}
        for k, v in ANOMALY_TYPES.items()
    ]
