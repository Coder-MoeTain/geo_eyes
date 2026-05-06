import pytest
from fastapi import HTTPException

from app.services.model_service import ensure_active_model_or_error


def test_no_active_model_raises_explicit_error():
    with pytest.raises(HTTPException) as exc:
        ensure_active_model_or_error(None)
    assert exc.value.status_code == 400
    detail = exc.value.detail
    assert detail["error"] == "No active aircraft detection model found"

