"""Unit tests for GDriveClient lazy initialization."""

import time
import unittest.mock as mock

import pytest

from slipstream.integrations.gdrive import GDriveClient

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_google_build():
    """Mock the build function to track when it's called."""
    with mock.patch("slipstream.integrations.gdrive.build") as m:
        yield m


def test_init_does_not_call_build(mock_google_build):
    """CRITICAL: __init__ should NOT call build() - lazy initialization only."""
    client = GDriveClient()
    mock_google_build.assert_not_called()
    assert client.max_workers == 4


def test_first_service_access_calls_build(mock_google_build):
    """First access to service property should trigger build() call."""
    mock_service = mock.Mock()
    mock_google_build.return_value = mock_service

    client = GDriveClient()
    mock_google_build.assert_not_called()

    # Access service for the first time
    service = client.service

    mock_google_build.assert_called_once_with("drive", "v3")
    assert service is mock_service


def test_subsequent_service_access_reuses_cached(mock_google_build):
    """Subsequent accesses to service should reuse cached instance."""
    mock_service = mock.Mock()
    mock_google_build.return_value = mock_service

    client = GDriveClient()

    service1 = client.service
    service2 = client.service
    service3 = client.service

    # build() called exactly once, not three times
    mock_google_build.assert_called_once_with("drive", "v3")
    assert service1 is service2 is service3


def test_multiple_clients_independent_services(mock_google_build):
    """Each GDriveClient instance should have its own service."""
    mock_service1 = mock.Mock(name="service1")
    mock_service2 = mock.Mock(name="service2")
    mock_google_build.side_effect = [mock_service1, mock_service2]

    client1 = GDriveClient()
    client2 = GDriveClient()

    service1 = client1.service
    service2 = client2.service

    assert mock_google_build.call_count == 2
    assert service1 is not service2


def test_instance_service_independent_from_thread_local(mock_google_build):
    """Instance service and thread-local service should be independent.

    This verifies that:
    1. Client instance service uses lazy property pattern
    2. Thread-local service (used by download_single_file) is independent
    3. Both can coexist without interference
    """
    from slipstream.integrations.gdrive import _get_thread_service

    mock_instance_service = mock.Mock(name="instance_service")
    mock_thread_service = mock.Mock(name="thread_service")

    # First call -> instance service, second call -> thread service
    mock_google_build.side_effect = [mock_instance_service, mock_thread_service]

    # Create client and access instance service
    client = GDriveClient()
    instance_service = client.service

    # Call thread-local service function
    thread_service = _get_thread_service()

    # Verify two separate build() calls
    assert mock_google_build.call_count == 2

    # Verify they are different services
    assert instance_service is mock_instance_service
    assert thread_service is mock_thread_service
    assert instance_service is not thread_service


def test_service_property_exception_handling(mock_google_build):
    """If build() fails, the exception should propagate clearly."""
    from googleapiclient.errors import HttpError

    error = HttpError(mock.Mock(status=403), b"Permission denied")
    mock_google_build.side_effect = error

    client = GDriveClient()

    with pytest.raises(HttpError):
        _ = client.service


def test_service_property_retry_after_failure(mock_google_build):
    """If build() fails once, it should retry on next access."""
    from googleapiclient.errors import HttpError

    error = HttpError(mock.Mock(status=503), b"Service unavailable")
    success_service = mock.Mock()
    mock_google_build.side_effect = [error, success_service]

    client = GDriveClient()

    # First access fails
    with pytest.raises(HttpError):
        _ = client.service

    # Second access retries and succeeds
    service = client.service
    assert service is success_service
    assert mock_google_build.call_count == 2


def test_lazy_init_performance_improvement(mock_google_build):
    """Lazy initialization should make instantiation significantly faster."""

    def slow_build(*args, **kwargs):
        time.sleep(0.1)  # Simulate 100ms overhead
        return mock.Mock()

    mock_google_build.side_effect = slow_build

    # Measure instantiation (should be fast)
    start = time.time()
    client = GDriveClient()
    init_time = time.time() - start

    assert init_time < 0.01, f"Init took {init_time:.3f}s, expected < 0.01s"

    # Measure first service access (should be slow)
    start = time.time()
    _ = client.service
    access_time = time.time() - start

    assert access_time >= 0.1, f"Access took {access_time:.3f}s, expected >= 0.1s"
