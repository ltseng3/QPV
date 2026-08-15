from __future__ import annotations

import json
import logging

from qorchsim.logging import JsonFormatter, get_logger


def test_json_formatter_and_context_logger() -> None:
    record = logging.LogRecord("qorchsim.test", logging.INFO, __file__, 1, "started", (), None)
    record.run_id = "run-1"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["run_id"] == "run-1"
    assert payload["message"] == "started"

    logger = get_logger("qorchsim.test", {"run_id": "run-1"}).child(round_id="round-1")
    assert logger.extra == {"run_id": "run-1", "round_id": "round-1"}
