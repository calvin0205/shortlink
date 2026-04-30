"""
Rule-based AI engine for OT/IoT security incident analysis.
Falls back gracefully — no external API required.
Optional: set ANTHROPIC_API_KEY env var to use Claude API instead.
"""
from typing import Optional

# ── Knowledge base ────────────────────────────────────────────────────────────

KNOWLEDGE_BASE = {
    "unauthorized_access": {
        "keywords": ["unauthorized", "access", "login", "authentication", "credential", "password", "account"],
        "analysis": "Unauthorized access attempts indicate a potential credential-based attack. In OT environments, this is critical as it may lead to unauthorized control of physical processes.",
        "recommendations": [
            "Immediately lock the affected account and rotate credentials",
            "Enable multi-factor authentication (MFA) for all OT system accounts",
            "Review access logs for the past 24-48 hours for other suspicious activity",
            "Isolate the affected device from the network if active intrusion is suspected",
            "Check for lateral movement to other devices on the same network segment",
            "Update firewall rules to restrict access to the device from unknown IPs",
        ],
        "references": ["IEC 62443-3-3 SR 1.1", "NIST SP 800-82 Rev.3", "NERC CIP-007"],
        "severity_note": "High priority in OT environments — unauthorized access to PLCs or RTUs can cause physical process disruption.",
    },
    "firmware_tamper": {
        "keywords": ["firmware", "tamper", "modification", "hash", "version", "update", "flash"],
        "analysis": "Firmware tampering is one of the most serious threats in OT security. Modified firmware can introduce backdoors, alter control logic, or cause device malfunction.",
        "recommendations": [
            "Immediately take the device offline and initiate incident response procedures",
            "Compare current firmware hash against known-good baseline from vendor",
            "Do not restart or reconfigure the device — preserve forensic evidence",
            "Contact the device vendor for emergency firmware validation support",
            "Review supply chain for potential hardware/firmware compromise",
            "Implement firmware signing and secure boot if not already in place",
            "Audit all firmware update procedures and access controls",
        ],
        "references": ["IEC 62443-4-2 CR 3.4", "NIST SP 800-193", "ICS-CERT Advisory"],
        "severity_note": "Critical — firmware compromise can persist through reboots and is difficult to detect without baseline comparison.",
    },
    "protocol_anomaly": {
        "keywords": ["protocol", "anomaly", "modbus", "dnp3", "iec104", "command", "injection", "packet"],
        "analysis": "Protocol anomalies in OT networks often indicate command injection or replay attacks targeting industrial control protocols like Modbus, DNP3, or IEC 60870-5-104.",
        "recommendations": [
            "Deploy an OT-specific intrusion detection system (IDS) like Claroty or Dragos",
            "Capture and analyze network traffic for full packet inspection",
            "Implement protocol whitelisting — only allow expected function codes",
            "Segment OT network using industrial DMZ architecture",
            "Validate all control commands against expected operational parameters",
            "Review process historian for unexpected setpoint changes",
        ],
        "references": ["IEC 62443-3-2", "NIST SP 800-82 Rev.3 Section 5.2", "ISA-99"],
        "severity_note": "High — protocol anomalies targeting ICS protocols can directly manipulate physical processes.",
    },
    "config_change": {
        "keywords": ["configuration", "config", "setting", "parameter", "modified", "changed", "unauthorized change"],
        "analysis": "Unauthorized configuration changes in OT systems can alter device behavior, open security vulnerabilities, or cause process instability.",
        "recommendations": [
            "Compare current configuration against last known-good backup",
            "Identify what was changed and assess operational impact",
            "Restore from verified backup if change was unauthorized",
            "Implement change management controls with approval workflow",
            "Enable configuration change alerting on all critical devices",
            "Review who had access to the device during the change window",
        ],
        "references": ["IEC 62443-2-1 Element 4.3.4", "NIST SP 800-82", "NERC CIP-010"],
        "severity_note": "Medium to High — depends on what was changed. Safety system changes are critical.",
    },
    "brute_force": {
        "keywords": ["brute force", "brute-force", "multiple failed", "login attempt", "password spray", "dictionary attack"],
        "analysis": "Brute force attacks against OT devices suggest an attacker is attempting to gain unauthorized access, possibly after network reconnaissance.",
        "recommendations": [
            "Implement account lockout after 3-5 failed attempts",
            "Block the source IP at the firewall immediately",
            "Enable alerting for repeated authentication failures",
            "Review whether the device should be exposed to this network segment",
            "Consider deploying a jump server/bastion host for OT device access",
            "Audit all accounts on the affected device for unauthorized additions",
        ],
        "references": ["IEC 62443-3-3 SR 1.11", "NIST SP 800-82", "CIS Controls v8"],
        "severity_note": "High — brute force is often a precursor to successful compromise.",
    },
    "network_scan": {
        "keywords": ["scan", "reconnaissance", "port scan", "nmap", "discovery", "probe", "enumeration"],
        "analysis": "Network scanning targeting OT devices indicates active reconnaissance. Attackers scan to identify device types, open ports, and vulnerabilities before launching targeted attacks.",
        "recommendations": [
            "Identify the scanning source IP and block it at the perimeter",
            "Review network segmentation — OT devices should not be reachable from IT networks",
            "Enable network traffic monitoring to detect future scanning activity",
            "Audit firewall rules to ensure minimal exposure of OT devices",
            "Check if scan revealed any previously unknown open ports or services",
            "Update network topology documentation based on scan findings",
        ],
        "references": ["IEC 62443-3-2 SL 2", "NIST SP 800-82 Section 6.2", "CISA Advisory"],
        "severity_note": "Medium — scanning itself is not an attack but indicates pre-attack activity.",
    },
    "comm_timeout": {
        "keywords": ["timeout", "communication", "connection lost", "unreachable", "offline", "network disruption"],
        "analysis": "Communication timeouts can indicate network disruption, DoS attacks, or hardware failures. In OT environments, loss of communication with critical devices requires immediate investigation.",
        "recommendations": [
            "Verify physical network connectivity to the device",
            "Check for network congestion or bandwidth saturation",
            "Review switch/router logs for port errors or link flapping",
            "Investigate whether timeout correlates with other anomalous activity",
            "Ensure redundant communication paths are operational",
            "Contact operations team to verify physical device status",
        ],
        "references": ["IEC 62443-3-3 SR 7.6", "NIST SP 800-82"],
        "severity_note": "Medium — may indicate DoS attack or hardware failure. Escalate if multiple devices affected simultaneously.",
    },
    "memory_overflow": {
        "keywords": ["memory", "overflow", "buffer", "heap", "stack", "crash", "exploit"],
        "analysis": "Memory overflow warnings may indicate exploitation attempts or software vulnerabilities. In OT devices with legacy software, buffer overflows are a common attack vector.",
        "recommendations": [
            "Review device logs for crash dumps or error codes",
            "Apply vendor-supplied patches if a known vulnerability exists",
            "Implement network-based protection (virtual patching) if patching is not immediately possible",
            "Isolate the device if exploitation is confirmed",
            "Contact vendor for emergency support and patching guidance",
            "Consider deploying a WAF or protocol-aware IDS to filter malformed requests",
        ],
        "references": ["IEC 62443-4-2 CR 3.9", "CVE Database", "ICS-CERT Advisories"],
        "severity_note": "High — if confirmed exploitation, immediate isolation required.",
    },
    "unusual_traffic": {
        "keywords": ["traffic", "bandwidth", "exfiltration", "data transfer", "unusual", "anomalous", "outbound"],
        "analysis": "Unusual network traffic from OT devices may indicate data exfiltration, C2 communication, or lateral movement by an attacker who has already compromised the device.",
        "recommendations": [
            "Capture and analyze the unusual traffic using Wireshark or similar",
            "Identify destination IPs and check against threat intelligence feeds",
            "Block outbound connections from OT devices to internet/unknown IPs",
            "Review whether the device should have any outbound connectivity",
            "Check for unauthorized software or processes running on the device",
            "Implement egress filtering at the OT network perimeter",
        ],
        "references": ["IEC 62443-3-3 SR 5.2", "NIST SP 800-82", "MITRE ATT&CK for ICS"],
        "severity_note": "High — unusual outbound traffic from OT devices is a strong indicator of compromise.",
    },
    "sensor_manipulation": {
        "keywords": ["sensor", "manipulation", "spoofing", "false reading", "data integrity", "measurement"],
        "analysis": "Sensor data manipulation is a sophisticated attack targeting process integrity. False sensor readings can cause operators to make wrong decisions or trigger unsafe automated responses.",
        "recommendations": [
            "Cross-validate sensor readings with redundant sensors or physical inspection",
            "Check for physical tampering of the sensor hardware",
            "Review sensor calibration records and last known-good readings",
            "Alert process engineers to verify operational parameters manually",
            "Implement sensor data validation rules (range checks, rate-of-change limits)",
            "Consider deploying an anomaly detection system for process data",
        ],
        "references": ["IEC 62443-3-3 SR 3.5", "NIST SP 800-82", "MITRE ATT&CK for ICS T0831"],
        "severity_note": "Critical — sensor manipulation can cause physical damage, safety incidents, or environmental harm.",
    },
    "general": {
        "keywords": [],
        "analysis": "OT/IoT security incidents require a structured response following established frameworks such as IEC 62443 and NIST SP 800-82.",
        "recommendations": [
            "Follow your organization's incident response plan",
            "Document all observations and actions taken with timestamps",
            "Preserve logs and forensic evidence before making changes",
            "Notify relevant stakeholders including operations, security, and management",
            "Consider engaging an OT security specialist for complex incidents",
            "Review the incident for lessons learned and process improvements",
        ],
        "references": ["IEC 62443", "NIST SP 800-82 Rev.3", "CISA ICS Security"],
        "severity_note": "Follow escalation procedures defined in your incident response plan.",
    },
}

DEVICE_GUIDANCE = {
    "PLC": "PLCs control physical processes directly. Any compromise has immediate safety and operational implications. Prioritize isolation and physical verification.",
    "RTU": "RTUs are critical for SCADA communication. Compromise can affect wide-area monitoring and control. Check all connected field devices.",
    "HMI": "HMIs are common entry points for OT attacks due to Windows-based OS. Ensure antivirus is updated and remote access is restricted.",
    "Gateway": "Gateways bridge IT and OT networks — a compromised gateway can provide attackers with direct OT access. Review all connected network segments.",
    "Sensor": "Sensor compromise affects data integrity. Cross-validate with redundant measurements and physical inspection.",
}


def _match_knowledge(message: str, anomaly_type: Optional[str] = None) -> dict:
    """Find the best matching knowledge base entry."""
    msg_lower = message.lower()

    # If anomaly_type provided, use it directly
    if anomaly_type and anomaly_type in KNOWLEDGE_BASE:
        return KNOWLEDGE_BASE[anomaly_type]

    # Keyword matching
    best_match = None
    best_score = 0
    for key, entry in KNOWLEDGE_BASE.items():
        if key == "general":
            continue
        score = sum(1 for kw in entry["keywords"] if kw in msg_lower)
        if score > best_score:
            best_score = score
            best_match = entry

    return best_match if best_match else KNOWLEDGE_BASE["general"]


def analyze_incident(incident: dict) -> dict:
    """Generate analysis for a specific incident."""
    anomaly_type = None
    # Try to infer anomaly type from incident title/description
    title_lower = incident.get("title", "").lower()
    desc_lower = incident.get("description", "").lower()
    combined = title_lower + " " + desc_lower

    for key, entry in KNOWLEDGE_BASE.items():
        if key == "general":
            continue
        if any(kw in combined for kw in entry["keywords"]):
            anomaly_type = key
            break

    kb = KNOWLEDGE_BASE.get(anomaly_type, KNOWLEDGE_BASE["general"])

    severity = incident.get("severity", "medium")
    risk_score = incident.get("risk_score", 50)

    answer = (
        f"**Incident Analysis: {incident.get('title', 'Security Incident')}**\n\n"
        f"{kb['analysis']}\n\n"
        f"**Risk Assessment**: Risk score {risk_score}/100 — this is classified as **{severity.upper()}** severity. "
        f"{kb['severity_note']}"
    )

    return {
        "answer": answer,
        "recommendations": kb["recommendations"],
        "references": kb["references"],
        "severity_assessment": f"{severity.upper()} (Score: {risk_score}/100)",
    }


GENERAL_RESPONSES = {
    "iec62443": {
        "keywords": ["iec 62443", "iec62443", "62443"],
        "answer": "**IEC 62443 — OT Security Standard**\n\nIEC 62443 is the international standard series for Industrial Automation and Control Systems (IACS) security. It defines security requirements and processes for OT/ICS environments.\n\n**Key components:**\n• **62443-1**: General concepts and terminology\n• **62443-2**: Policies, procedures, and organizational security\n• **62443-3**: System-level security requirements and Security Levels (SL 1-4)\n• **62443-4**: Component-level security requirements\n\n**Security Levels:**\n• SL1 — Protection against casual/unintentional violations\n• SL2 — Protection against intentional violation with simple means\n• SL3 — Protection against sophisticated attacks\n• SL4 — Protection against state-sponsored attacks",
        "recommendations": ["Perform an IEC 62443 gap assessment", "Define target Security Levels for each zone", "Implement a Security Management System per 62443-2-1", "Ensure component procurement requirements include 62443-4-2 compliance"],
        "references": ["IEC 62443-1-1", "IEC 62443-2-1", "IEC 62443-3-3", "IEC 62443-4-2"],
    },
    "nist": {
        "keywords": ["nist", "sp 800-82", "800-82"],
        "answer": "**NIST SP 800-82 — Guide to ICS Security**\n\nNIST Special Publication 800-82 provides guidance for securing Industrial Control Systems including SCADA, DCS, PLC, and other OT systems.\n\n**Key areas covered:**\n• ICS threat landscape and vulnerabilities\n• Security architecture recommendations\n• Network segmentation and DMZ design\n• Incident response for ICS environments\n• Risk management framework application to ICS",
        "recommendations": ["Apply NIST Risk Management Framework (RMF) to OT systems", "Implement the ICS security architecture with IT/OT network separation", "Follow NIST incident response guidelines", "Conduct regular risk assessments using NIST methodology"],
        "references": ["NIST SP 800-82 Rev.3", "NIST SP 800-37", "NIST CSF 2.0"],
    },
    "risk_score": {
        "keywords": ["risk score", "how is risk", "risk calculation", "score calculated", "risk scoring"],
        "answer": "**OT Sentinel Risk Scoring Methodology**\n\nRisk scores (0–100) are calculated using two factors:\n\n**1. Anomaly Type Base Score:**\n• Sensor Manipulation: 78–94\n• Unauthorized Access: 82–96\n• Firmware Tampering: 78–92\n• Brute Force: 72–88\n• Protocol Anomaly: 68–84\n• Config Change: 62–78\n• Unusual Traffic: 52–68\n• Network Scan: 55–72\n• Memory Overflow: 42–58\n• Comm Timeout: 35–52\n\n**2. Device Type Multiplier:**\n• PLC: ×1.20 (controls physical processes)\n• RTU: ×1.15\n• HMI: ×1.10\n• Gateway: ×1.05\n• Sensor: ×1.00\n\n**Severity Mapping:** Critical ≥80 · High 60–79 · Medium 40–59 · Low <40",
        "recommendations": ["Focus remediation on Critical (≥80) scores first", "PLCs with any anomaly should be prioritized due to 1.2x multiplier", "Review Medium scores proactively to prevent escalation"],
        "references": ["IEC 62443-3-2", "NIST SP 800-30"],
    },
    "mitre": {
        "keywords": ["mitre", "att&ck", "attack framework", "ics tactics"],
        "answer": "**MITRE ATT&CK for ICS**\n\nMITRE ATT&CK for ICS is a knowledge base of adversary tactics and techniques specifically for Industrial Control Systems.\n\n**Key Tactic Categories:**\n• Initial Access — spear phishing, exploit public-facing apps\n• Execution — command-line, scripting\n• Persistence — modify program, hooking\n• Evasion — rootkit, masquerading\n• Discovery — remote system discovery, network sniffing\n• Lateral Movement — exploitation of remote services\n• Collection — automated collection, point & tag identification\n• **Impact — Manipulation of Control (T0831), Loss of Safety (T0837), Damage to Property (T0879)**",
        "recommendations": ["Map detected incidents to MITRE ATT&CK for ICS techniques", "Use the framework for threat hunting in OT environments", "Develop detection rules based on ICS-specific TTPs"],
        "references": ["MITRE ATT&CK for ICS", "ICS-CERT Advisories", "CISA AA22-265A"],
    },
    "network_segmentation": {
        "keywords": ["network segmentation", "dmz", "zone", "purdue", "conduit", "it ot separation", "air gap"],
        "answer": "**OT Network Segmentation Best Practices**\n\nProper network segmentation is the most effective control for preventing IT-to-OT lateral movement.\n\n**Purdue Model Zones:**\n• Level 0 — Physical process (sensors, actuators)\n• Level 1 — Intelligent devices (PLCs, RTUs)\n• Level 2 — Control systems (HMI, SCADA)\n• Level 3 — Manufacturing operations (historian, MES)\n• **DMZ** — Boundary between IT and OT\n• Level 4/5 — Enterprise IT\n\n**Key Controls:**\n• Industrial DMZ with dual firewalls\n• Data diodes for one-way communication\n• Jump servers for remote access\n• No direct internet connectivity for OT devices",
        "recommendations": ["Implement industrial DMZ between IT and OT networks", "Deploy unidirectional gateways for historian data", "Use jump servers for all OT remote access", "Disable unnecessary protocols and ports at zone boundaries"],
        "references": ["IEC 62443-3-2", "NIST SP 800-82 Section 5.3", "ISA-99 Zone Model"],
    },
}


def process_query(message: str, incident: Optional[dict] = None) -> dict:
    """
    Main query processor. Returns structured response dict.
    """
    msg_lower = message.lower()

    # If incident context provided, prioritize incident-specific analysis
    if incident:
        result = analyze_incident(incident)
        result["incident_context"] = {
            "incident_id": incident.get("incident_id", ""),
            "title": incident.get("title", ""),
            "severity": incident.get("severity", ""),
            "device_name": incident.get("device_name", ""),
            "status": incident.get("status", ""),
            "risk_score": int(incident.get("risk_score", 0)),
        }
        result["source"] = "rule-based"
        return result

    # Check general knowledge topics first (specific enough to match before keyword search)
    for topic, data in GENERAL_RESPONSES.items():
        if any(kw in msg_lower for kw in data["keywords"]):
            return {
                "answer": data["answer"],
                "recommendations": data["recommendations"],
                "references": data["references"],
                "severity_assessment": None,
                "incident_context": None,
                "source": "rule-based",
            }

    # Device-specific question
    if any(d.lower() in msg_lower for d in ["plc", "rtu", "hmi", "gateway", "sensor"]):
        device_type = next((d for d in ["PLC", "RTU", "HMI", "Gateway", "Sensor"] if d.lower() in msg_lower), None)
        guidance = DEVICE_GUIDANCE.get(device_type, "")
        kb = _match_knowledge(message)
        answer = f"**{device_type} Security Guidance**\n\n{guidance}"
        if kb != KNOWLEDGE_BASE["general"]:
            answer += f"\n\n**Threat Context**\n\n{kb['analysis']}"
        return {
            "answer": answer,
            "recommendations": kb["recommendations"],
            "references": kb["references"],
            "severity_assessment": kb.get("severity_note"),
            "incident_context": None,
            "source": "rule-based",
        }

    # Security threat keyword matching
    kb = _match_knowledge(message)

    if kb != KNOWLEDGE_BASE["general"]:
        # Matched a specific threat category
        if any(w in msg_lower for w in ["how", "steps", "procedure", "should i", "what should", "respond", "handle", "fix"]):
            answer = f"**Response Procedure**\n\n{kb['analysis']}\n\nFollow the steps below to address this effectively."
        else:
            answer = f"**Threat Analysis**\n\n{kb['analysis']}\n\n⚠️ {kb['severity_note']}"
    else:
        # General fallback — vary by question type
        if any(w in msg_lower for w in ["help", "start", "begin", "overview", "introduction"]):
            answer = ("**OT Sentinel — Getting Started**\n\n"
                      "OT Sentinel monitors OT/IoT devices for security anomalies. Here's what you can do:\n\n"
                      "• **Simulate Anomaly** — Go to Devices page and click ⚡ to trigger a simulated attack\n"
                      "• **Investigate Incidents** — Review incidents on the Incidents page, acknowledge and resolve them\n"
                      "• **Ask me anything** — Ask about specific threats (firmware tampering, unauthorized access, etc.)\n"
                      "• **Select an incident** — Use the dropdown above to get context-aware analysis\n\n"
                      "Try asking about: IEC 62443, risk scoring, network segmentation, or specific device types.")
        elif any(w in msg_lower for w in ["risk", "score", "severity", "dangerous"]):
            answer = ("**Risk Assessment Overview**\n\n"
                      "OT Sentinel uses a 0–100 risk scoring system. Scores are calculated from:\n"
                      "• Anomaly type severity (e.g., unauthorized access scores higher than comm timeout)\n"
                      "• Device type multiplier (PLCs score 1.2x higher due to physical process impact)\n\n"
                      "Ask me 'how is risk score calculated' for the full breakdown.")
        elif any(w in msg_lower for w in ["what", "explain", "tell me", "describe"]):
            answer = ("**OT/ICS Security Overview**\n\n"
                      "OT (Operational Technology) security protects industrial control systems from cyber threats. "
                      "Unlike IT security, OT attacks can cause physical damage, safety incidents, or environmental harm.\n\n"
                      "Key threats in OT environments:\n"
                      "• Unauthorized access to PLCs/RTUs\n• Firmware tampering\n• Protocol anomalies (Modbus, DNP3)\n"
                      "• Sensor data manipulation\n• Network reconnaissance\n\n"
                      "Try asking about a specific threat or select an incident from the dropdown for detailed analysis.")
        else:
            answer = ("**Security Advisory**\n\n"
                      "I can help you analyze OT/ICS security threats. Try asking about:\n\n"
                      "• A specific threat type (e.g., 'explain firmware tampering')\n"
                      "• A device type (e.g., 'how to secure a PLC')\n"
                      "• A standard (e.g., 'what is IEC 62443')\n"
                      "• Risk scoring methodology\n"
                      "• Network segmentation best practices\n\n"
                      "Or select an incident from the dropdown above for context-aware analysis.")

    return {
        "answer": answer,
        "recommendations": kb["recommendations"],
        "references": kb["references"],
        "severity_assessment": kb.get("severity_note"),
        "incident_context": None,
        "source": "rule-based",
    }
