import json
import pytest
from io import StringIO
from datetime import datetime

from src.grace.logger import GraceLogger


class TestGraceLogger:
    def test_log_returns_dict_with_all_fields(self):
        stream = StringIO()
        log = GraceLogger(stream)
        result = log.log("M-TEST", "test_fn", "TEST_BLOCK", "test event")
        assert isinstance(result, dict)
        assert result["module"] == "M-TEST"
        assert result["fn"] == "test_fn"
        assert result["block"] == "TEST_BLOCK"
        assert result["event"] == "test event"
        assert result["result"] == "ok"
        assert "trace_id" in result
        assert "scenario_id" in result
        assert "timestamp" in result

    def test_log_writes_json_to_stream(self):
        stream = StringIO()
        log = GraceLogger(stream)
        log.log("M-X", "f", "B", "e", result="fail")
        stream.seek(0)
        line = stream.readline()
        data = json.loads(line)
        assert data["module"] == "M-X"
        assert data["result"] == "fail"

    def test_custom_trace_and_scenario(self):
        stream = StringIO()
        log = GraceLogger(stream)
        log.log("M-T", "f", "B", "e", trace_id="TRACE-1", scenario_id="SCN-A")
        stream.seek(0)
        data = json.loads(stream.readline())
        assert data["trace_id"] == "TRACE-1"
        assert data["scenario_id"] == "SCN-A"

    def test_timestamp_is_iso_format(self):
        stream = StringIO()
        log = GraceLogger(stream)
        log.log("M-T", "f", "B", "e")
        stream.seek(0)
        data = json.loads(stream.readline())
        ts = data["timestamp"]
        datetime.fromisoformat(ts)

    def test_default_result_is_ok(self):
        stream = StringIO()
        log = GraceLogger(stream)
        result = log.log("M-T", "f", "B", "e")
        assert result["result"] == "ok"

    def test_default_trace_and_scenario_are_empty(self):
        stream = StringIO()
        log = GraceLogger(stream)
        result = log.log("M-T", "f", "B", "e")
        assert result["trace_id"] == ""
        assert result["scenario_id"] == ""
