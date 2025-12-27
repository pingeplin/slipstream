import pytest


@pytest.mark.unit
def test_import():
    import slipstream

    assert slipstream is not None
