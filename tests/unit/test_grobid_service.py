"""Unit tests cho extraction/grobid_service.py — GROBID Service Manager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestGrobidServiceManager:
    """Test GrobidServiceManager class."""

    def test_initialization(self):
        """Test manager initialization."""
        from integrity_checker.extraction.grobid_service import GrobidServiceManager
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig(enabled=True, url="http://localhost:8070")
        manager = GrobidServiceManager(config=config)

        assert manager.config == config
        assert manager.url == "http://localhost:8070"
        assert manager._container_name == "essay-check-grobid"

    def test_status_unknown_when_no_docker(self):
        """Test status is unknown when Docker not available."""
        from integrity_checker.extraction.grobid_service import (
            GrobidServiceManager,
            GROBID_STATUS,
        )
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig(enabled=True)

        with patch.object(GrobidServiceManager, "_check_docker_available"):
            with patch.object(GrobidServiceManager, "_check_docker_sdk", return_value=False):
                manager = GrobidServiceManager(config=config)
                # Status should be unknown when Docker SDK not available
                assert manager._status == GROBID_STATUS.UNKNOWN

    def test_is_available_property(self):
        """Test is_available property."""
        from integrity_checker.extraction.grobid_service import (
            GrobidServiceManager,
            GROBID_STATUS,
        )
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig()

        with patch.object(GrobidServiceManager, "_check_docker_available"):
            with patch.object(GrobidServiceManager, "_check_docker_sdk", return_value=False):
                manager = GrobidServiceManager(config=config)
                manager._status = GROBID_STATUS.AVAILABLE
                assert manager.is_available is True

                manager._status = GROBID_STATUS.UNHEALTHY
                assert manager.is_available is False

    def test_stats_initialization(self):
        """Test stats are initialized correctly."""
        from integrity_checker.extraction.grobid_service import GrobidServiceManager
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig()
        manager = GrobidServiceManager(config=config)

        assert manager.stats.total_requests == 0
        assert manager.stats.successful_requests == 0
        assert manager.stats.failed_requests == 0
        assert manager.stats.cache_hits == 0
        assert manager.stats.cache_misses == 0

    def test_get_stats(self):
        """Test get_stats returns correct format."""
        from integrity_checker.extraction.grobid_service import (
            GrobidServiceManager,
            GROBID_STATUS,
        )
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig()
        manager = GrobidServiceManager(config=config)
        manager._status = GROBID_STATUS.AVAILABLE

        stats = manager.get_stats()
        assert "status" in stats
        assert "url" in stats
        assert "stats" in stats
        assert stats["stats"]["total_requests"] == 0


class TestGrobidStatus:
    """Test GROBID_STATUS enum."""

    def test_status_values(self):
        """Test GROBID_STATUS enum values."""
        from integrity_checker.extraction.grobid_service import GROBID_STATUS

        assert GROBID_STATUS.AVAILABLE.value == "available"
        assert GROBID_STATUS.UNHEALTHY.value == "unhealthy"
        assert GROBID_STATUS.STOPPED.value == "stopped"
        assert GROBID_STATUS.STARTING.value == "starting"
        assert GROBID_STATUS.UNKNOWN.value == "unknown"


class TestCacheOperations:
    """Test cache operations."""

    def test_get_cache_path(self, tmp_path):
        """Test cache path generation."""
        from integrity_checker.extraction.grobid_service import GrobidServiceManager
        from integrity_checker.config import GrobidConfig
        from integrity_checker.config import Settings

        config = GrobidConfig()
        manager = GrobidServiceManager(config=config)

        with patch.object(manager, "_check_docker_available"):
            with patch.object(manager, "_check_docker_sdk", return_value=False):
                # Mock get_settings
                mock_settings = MagicMock()
                mock_settings.paths.grobid_output_dir = tmp_path / "cache" / "grobid"
                with patch(
                    "integrity_checker.extraction.grobid_service.get_settings",
                    return_value=mock_settings,
                ):
                    cache_path = manager.get_cache_path("/test/file.pdf")
                    # Path should end with .tei.xml (not just .xml)
                    assert str(cache_path).endswith(".tei.xml")
                    assert cache_path.parent.name == "grobid"

    def test_cache_hit(self, tmp_path):
        """Test cache hit returns content."""
        from integrity_checker.extraction.grobid_service import GrobidServiceManager
        from integrity_checker.config import GrobidConfig
        import hashlib

        config = GrobidConfig(cache_by_file_sha256=True)
        manager = GrobidServiceManager(config=config)

        with patch.object(manager, "_check_docker_available"):
            with patch.object(manager, "_check_docker_sdk", return_value=False):
                # Create a fake cache file
                cache_dir = tmp_path / "grobid"
                cache_dir.mkdir(parents=True, exist_ok=True)

                # Create a real test file to get SHA256
                test_file = tmp_path / "test.pdf"
                test_file.write_bytes(b"PDF content")

                # Compute SHA256 of the test file
                sha = hashlib.sha256(test_file.read_bytes()).hexdigest()

                cache_file = cache_dir / f"{sha}.tei.xml"
                cache_file.write_text("<TEI>test</TEI>")

                mock_settings = MagicMock()
                mock_settings.paths.grobid_output_dir = cache_dir
                with patch(
                    "integrity_checker.extraction.grobid_service.get_settings",
                    return_value=mock_settings,
                ):
                    result = manager.get_from_cache(str(test_file))
                    assert result == "<TEI>test</TEI>"
                    assert manager.stats.cache_hits == 1

    def test_cache_miss(self, tmp_path):
        """Test cache miss returns None."""
        from integrity_checker.extraction.grobid_service import GrobidServiceManager
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig(cache_by_file_sha256=True)
        manager = GrobidServiceManager(config=config)

        with patch.object(manager, "_check_docker_available"):
            with patch.object(manager, "_check_docker_sdk", return_value=False):
                cache_dir = tmp_path / "grobid"
                cache_dir.mkdir(parents=True, exist_ok=True)

                mock_settings = MagicMock()
                mock_settings.paths.grobid_output_dir = cache_dir
                with patch(
                    "integrity_checker.extraction.grobid_service.get_settings",
                    return_value=mock_settings,
                ):
                    result = manager.get_from_cache("/nonexistent/file.pdf")
                    assert result is None
                    assert manager.stats.cache_misses == 1

    def test_cache_disabled(self, tmp_path):
        """Test cache disabled returns None."""
        from integrity_checker.extraction.grobid_service import GrobidServiceManager
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig(cache_by_file_sha256=False)
        manager = GrobidServiceManager(config=config)

        with patch.object(manager, "_check_docker_available"):
            with patch.object(manager, "_check_docker_sdk", return_value=False):
                result = manager.get_from_cache("/test/file.pdf")
                assert result is None

    def test_save_to_cache(self, tmp_path):
        """Test saving to cache."""
        from integrity_checker.extraction.grobid_service import GrobidServiceManager
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig(cache_by_file_sha256=True)
        manager = GrobidServiceManager(config=config)

        with patch.object(manager, "_check_docker_available"):
            with patch.object(manager, "_check_docker_sdk", return_value=False):
                cache_dir = tmp_path / "grobid"

                mock_settings = MagicMock()
                mock_settings.paths.grobid_output_dir = cache_dir
                with patch(
                    "integrity_checker.extraction.grobid_service.get_settings",
                    return_value=mock_settings,
                ):
                    result = manager.save_to_cache("/test/file.pdf", "<TEI>test</TEI>")
                    assert result is True

                    # Verify file was created
                    cache_path = manager.get_cache_path("/test/file.pdf")
                    assert cache_path.exists()

    def test_invalidate_cache(self, tmp_path):
        """Test cache invalidation."""
        from integrity_checker.extraction.grobid_service import GrobidServiceManager
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig()
        manager = GrobidServiceManager(config=config)

        with patch.object(manager, "_check_docker_available"):
            with patch.object(manager, "_check_docker_sdk", return_value=False):
                cache_dir = tmp_path / "grobid"
                cache_dir.mkdir(parents=True, exist_ok=True)

                # Create some cache files
                (cache_dir / "test1.tei.xml").write_text("content1")
                (cache_dir / "test2.tei.xml").write_text("content2")

                mock_settings = MagicMock()
                mock_settings.paths.grobid_output_dir = cache_dir
                with patch(
                    "integrity_checker.extraction.grobid_service.get_settings",
                    return_value=mock_settings,
                ):
                    count = manager.invalidate_cache()
                    assert count == 2
                    assert not (cache_dir / "test1.tei.xml").exists()


class TestSingleton:
    """Test singleton pattern."""

    def test_get_grobid_manager_creates_singleton(self):
        """Test get_grobid_manager returns same instance."""
        from integrity_checker.extraction.grobid_service import (
            get_grobid_manager,
            reset_grobid_manager,
        )
        from integrity_checker.config import GrobidConfig

        reset_grobid_manager()

        config = GrobidConfig()
        manager1 = get_grobid_manager(config=config)
        manager2 = get_grobid_manager()

        assert manager1 is manager2

        # Cleanup
        reset_grobid_manager()

    def test_reset_clears_singleton(self):
        """Test reset clears singleton."""
        from integrity_checker.extraction.grobid_service import (
            get_grobid_manager,
            reset_grobid_manager,
        )
        from integrity_checker.config import GrobidConfig

        reset_grobid_manager()

        config = GrobidConfig()
        manager1 = get_grobid_manager(config=config)
        reset_grobid_manager()
        manager2 = get_grobid_manager(config=config)

        assert manager1 is not manager2


class TestHealthCheck:
    """Test health check functionality."""

    def test_check_health_with_mock(self):
        """Test health check with mocked container."""
        from integrity_checker.extraction.grobid_service import (
            GrobidServiceManager,
            GROBID_STATUS,
        )
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig()
        manager = GrobidServiceManager(config=config)

        with patch.object(manager, "_check_docker_available"):
            with patch.object(manager, "_check_docker_sdk", return_value=False):
                # Mock container status check
                with patch.object(
                    manager,
                    "_check_container_status",
                    return_value="running",
                ):
                    with patch("requests.get") as mock_get:
                        mock_response = MagicMock()
                        mock_response.status_code = 200
                        mock_get.return_value = mock_response

                        status = manager.check_health()
                        assert status == GROBID_STATUS.AVAILABLE

    def test_check_health_container_stopped(self):
        """Test health check when container stopped."""
        from integrity_checker.extraction.grobid_service import (
            GrobidServiceManager,
            GROBID_STATUS,
        )
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig()
        manager = GrobidServiceManager(config=config)

        with patch.object(manager, "_check_docker_available"):
            with patch.object(manager, "_check_docker_sdk", return_value=False):
                with patch.object(
                    manager,
                    "_check_container_status",
                    return_value="exited",
                ):
                    status = manager.check_health()
                    assert status == GROBID_STATUS.STOPPED


class TestAutoStart:
    """Test auto-start functionality."""

    def test_auto_start_when_not_available(self):
        """Test auto_start starts container when not available."""
        from integrity_checker.extraction.grobid_service import (
            GROBID_STATUS,
            get_grobid_manager,
            reset_grobid_manager,
        )
        from integrity_checker.config import GrobidConfig

        reset_grobid_manager()

        config = GrobidConfig()
        manager = get_grobid_manager(config=config, auto_start=False)

        # Mock start and wait_until_ready
        with patch.object(manager, "start", return_value=True) as mock_start:
            with patch.object(manager, "wait_until_ready", return_value=True):
                with patch.object(manager, "check_health") as mock_health:
                    mock_health.return_value = GROBID_STATUS.AVAILABLE

                    # Call with auto_start=True
                    manager2 = get_grobid_manager(config=config, auto_start=True)
                    # Manager should be the same
                    assert manager is manager2

        reset_grobid_manager()


class TestProcessPDF:
    """Test process_pdf functionality."""

    def test_process_pdf_increments_stats(self):
        """Test process_pdf increments stats."""
        from integrity_checker.extraction.grobid_service import GrobidServiceManager
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig()
        manager = GrobidServiceManager(config=config)

        with patch.object(manager, "_check_docker_available"):
            with patch.object(manager, "_check_docker_sdk", return_value=False):
                with patch(
                    "integrity_checker.extraction.grobid_parser.call_grobid_fulltext",
                    return_value="<TEI>test</TEI>",
                ):
                    result = manager.process_pdf("/test/file.pdf")
                    assert result == "<TEI>test</TEI>"
                    assert manager.stats.total_requests == 1
                    assert manager.stats.successful_requests == 1
                    assert manager.stats.last_used is not None

    def test_process_pdf_handles_failure(self):
        """Test process_pdf handles failures."""
        from integrity_checker.extraction.grobid_service import GrobidServiceManager
        from integrity_checker.config import GrobidConfig

        config = GrobidConfig()
        manager = GrobidServiceManager(config=config)

        with patch.object(manager, "_check_docker_available"):
            with patch.object(manager, "_check_docker_sdk", return_value=False):
                with patch(
                    "integrity_checker.extraction.grobid_parser.call_grobid_fulltext",
                    return_value="",  # Empty response = failure
                ):
                    result = manager.process_pdf("/test/file.pdf")
                    assert result == ""
                    assert manager.stats.total_requests == 1
                    assert manager.stats.failed_requests == 1
