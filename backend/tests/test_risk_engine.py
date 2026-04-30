"""Tests for the risk scoring engine."""
import pytest

from app.risk_engine import ANOMALY_TYPES, calculate_risk, get_anomaly_types


class TestCalculateRisk:
    def test_returns_four_tuple(self):
        risk_score, severity, title, description = calculate_risk("unauthorized_access", "Sensor")
        assert isinstance(risk_score, int)
        assert severity in ("critical", "high", "medium", "low")
        assert isinstance(title, str) and title
        assert isinstance(description, str) and description

    def test_risk_score_in_valid_range(self):
        for _ in range(20):
            risk_score, *_ = calculate_risk("unauthorized_access", "Sensor")
            assert 0 <= risk_score <= 100

    def test_all_anomaly_types_work(self):
        for anomaly_type in ANOMALY_TYPES:
            risk_score, severity, title, description = calculate_risk(anomaly_type, "Sensor")
            assert isinstance(risk_score, int)
            assert severity in ("critical", "high", "medium", "low")

    def test_plc_multiplier_increases_score_vs_sensor(self):
        import random
        random.seed(42)
        plc_score, *_ = calculate_risk("comm_timeout", "PLC")
        random.seed(42)
        sensor_score, *_ = calculate_risk("comm_timeout", "Sensor")
        # PLC multiplier (1.20) must yield a higher or equal score
        assert plc_score >= sensor_score

    def test_unknown_anomaly_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown anomaly type"):
            calculate_risk("nonexistent_type", "PLC")

    def test_severity_thresholds(self):
        import random
        # Test that severity maps correctly based on known score ranges
        # unauthorized_access on PLC: base 82-96, *1.20 => at least 98 which is critical
        for _ in range(10):
            score, severity, _, _ = calculate_risk("unauthorized_access", "PLC")
            assert score >= 80
            assert severity == "critical"

    def test_description_formats_device_name(self):
        _, _, _, description = calculate_risk("unauthorized_access", "Sensor")
        # description template uses {device_name} placeholder — it should NOT be formatted yet
        assert "{device_name}" in description

    def test_get_anomaly_types_returns_list(self):
        types = get_anomaly_types()
        assert isinstance(types, list)
        assert len(types) == len(ANOMALY_TYPES)
        for t in types:
            assert "value" in t
            assert "label" in t

    def test_get_anomaly_types_values_match_keys(self):
        types = get_anomaly_types()
        values = {t["value"] for t in types}
        assert values == set(ANOMALY_TYPES.keys())
