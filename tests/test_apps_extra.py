"""Additional tests for the apps module to improve coverage."""

import unittest
from unittest.mock import MagicMock, patch

from versiontracker.apps import (
    check_brew_install_candidates,
    _process_brew_batch,
    is_app_in_app_store,
    is_brew_cask_installable,
    get_homebrew_casks_list,
    SimpleRateLimiter,
)
from versiontracker.exceptions import (
    HomebrewError,
    NetworkError,
    BrewTimeoutError,
    BrewPermissionError,
)


class TestAppsExtra(unittest.TestCase):
    """Additional test cases for the apps module."""

    @patch("versiontracker.apps.is_homebrew_available")
    def test_check_brew_install_candidates_no_homebrew(self, mock_is_homebrew_available):
        """Test check_brew_install_candidates when Homebrew is not available."""
        # Mock is_homebrew_available to return False
        mock_is_homebrew_available.return_value = False
        
        # Mock data
        data = [("Firefox", "100.0"), ("Chrome", "99.0")]
        
        # Call the function
        result = check_brew_install_candidates(data)
        
        # Verify all apps are marked as not installable
        expected = [("Firefox", "100.0", False), ("Chrome", "99.0", False)]
        self.assertEqual(result, expected)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps._process_brew_batch")
    @patch("versiontracker.apps.smart_progress")
    def test_check_brew_install_candidates_success(
        self, mock_smart_progress, mock_process_brew_batch, mock_is_homebrew_available
    ):
        """Test check_brew_install_candidates with successful batch processing."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew_available.return_value = True
        
        # Mock _process_brew_batch to return expected results
        mock_process_brew_batch.return_value = [
            ("Firefox", "100.0", True),
            ("Chrome", "99.0", False)
        ]
        
        # Mock smart_progress to just pass through the iterable
        mock_smart_progress.side_effect = lambda x, **kwargs: x
        
        # Mock data
        data = [("Firefox", "100.0"), ("Chrome", "99.0")]
        
        # Call the function
        result = check_brew_install_candidates(data)
        
        # Verify the result
        expected = [("Firefox", "100.0", True), ("Chrome", "99.0", False)]
        self.assertEqual(result, expected)
        
        # Verify _process_brew_batch was called with correct arguments
        mock_process_brew_batch.assert_called_once_with(data, 1, True)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps._process_brew_batch")
    @patch("versiontracker.apps.smart_progress")
    def test_check_brew_install_candidates_network_error(
        self, mock_smart_progress, mock_process_brew_batch, mock_is_homebrew_available
    ):
        """Test check_brew_install_candidates handling network errors."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew_available.return_value = True
        
        # Mock _process_brew_batch to raise NetworkError
        mock_process_brew_batch.side_effect = NetworkError("Network unavailable")
        
        # Mock smart_progress to just pass through the iterable
        mock_smart_progress.side_effect = lambda x, **kwargs: x
        
        # Mock data
        data = [("Firefox", "100.0"), ("Chrome", "99.0")]
        
        # Test that NetworkError is re-raised
        with self.assertRaises(NetworkError):
            check_brew_install_candidates(data)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps._process_brew_batch")
    @patch("versiontracker.apps.smart_progress")
    def test_check_brew_install_candidates_batch_error_handling(
        self, mock_smart_progress, mock_process_brew_batch, mock_is_homebrew_available
    ):
        """Test check_brew_install_candidates handling batch processing errors."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew_available.return_value = True
        
        # Create a batch large enough to split into two
        data = [("App%d" % i, "1.0") for i in range(60)]
        
        # Make _process_brew_batch fail on first batch but succeed on second
        def side_effect(batch, rate_limit, use_cache):
            if batch[0][0] == "App0":  # First batch
                return [(name, version, False) for name, version in batch]
            else:  # Second batch
                return [(name, version, True) for name, version in batch]
                
        mock_process_brew_batch.side_effect = side_effect
        
        # Mock smart_progress to just pass through the iterable
        mock_smart_progress.side_effect = lambda x, **kwargs: x
        
        # Call the function
        result = check_brew_install_candidates(data)
        
        # Verify first 50 items are False, rest are True
        self.assertEqual(len(result), 60)
        for i, (name, _, installable) in enumerate(result):
            if i < 50:
                self.assertEqual(installable, False)
            else:
                self.assertEqual(installable, True)

    @patch("versiontracker.apps.is_homebrew_available")
    def test_process_brew_batch_no_homebrew(self, mock_is_homebrew_available):
        """Test _process_brew_batch when Homebrew is not available."""
        # Mock is_homebrew_available to return False
        mock_is_homebrew_available.return_value = False
        
        # Mock data
        data = [("Firefox", "100.0"), ("Chrome", "99.0")]
        
        # Call the function
        result = _process_brew_batch(data, 1, True)
        
        # Verify all apps are marked as not installable
        expected = [("Firefox", "100.0", False), ("Chrome", "99.0", False)]
        self.assertEqual(result, expected)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.is_brew_cask_installable")
    @patch("versiontracker.apps.ThreadPoolExecutor")
    def test_process_brew_batch_with_adaptive_rate_limiting(
        self, mock_executor_class, mock_is_installable, mock_is_homebrew
    ):
        """Test _process_brew_batch with adaptive rate limiting."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock ThreadPoolExecutor
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Mock is_brew_cask_installable to return True
        mock_is_installable.return_value = True
        
        # Mock Config object with adaptive_rate_limiting=True
        config = MagicMock()
        config.ui = {"adaptive_rate_limiting": True}
        
        with patch("versiontracker.apps.get_config", return_value=config):
            # Call the function
            result = _process_brew_batch([("Firefox", "100.0")], 1, True)
            
            # Verify the result
            expected = [("Firefox", "100.0", True)]
            self.assertEqual(result, expected)

    @patch("versiontracker.apps.read_cache")
    def test_is_app_in_app_store_cached(self, mock_read_cache):
        """Test is_app_in_app_store with cached data."""
        # Mock read_cache to return cached app store apps
        mock_read_cache.return_value = {"apps": ["Firefox", "Safari", "Pages"]}
        
        # Test with app in cache
        self.assertTrue(is_app_in_app_store("Firefox"))
        
        # Test with app not in cache
        self.assertFalse(is_app_in_app_store("Chrome"))

    @patch("versiontracker.apps.read_cache")
    def test_is_app_in_app_store_no_cache(self, mock_read_cache):
        """Test is_app_in_app_store without cache."""
        # Mock read_cache to return None (no cache)
        mock_read_cache.return_value = None
        
        # Test with use_cache=False
        self.assertFalse(is_app_in_app_store("Firefox", use_cache=False))

    @patch("versiontracker.apps.read_cache")
    def test_is_app_in_app_store_exception(self, mock_read_cache):
        """Test exception handling in is_app_in_app_store."""
        # Mock read_cache to raise an exception
        mock_read_cache.side_effect = Exception("Test error")
        
        # Test should return False on exception
        self.assertFalse(is_app_in_app_store("Firefox"))

    def test_simple_rate_limiter(self):
        """Test SimpleRateLimiter functionality."""
        # Create a rate limiter with a 0.2 second delay
        rate_limiter = SimpleRateLimiter(0.2)
        
        # Verify the delay was set (with minimum constraint)
        self.assertEqual(rate_limiter._delay, 0.2)
        
        # Test with lower than minimum delay
        min_limiter = SimpleRateLimiter(0.05)
        self.assertEqual(min_limiter._delay, 0.1)  # Should be clamped to 0.1
        
        # Test wait method
        import time
        start_time = time.time()
        rate_limiter.wait()  # First call should not wait
        after_first = time.time()
        rate_limiter.wait()  # Second call should wait
        after_second = time.time()
        
        # First call shouldn't have a significant delay
        self.assertLess(after_first - start_time, 0.1)
        
        # Second call should have a delay of approximately 0.2 seconds
        # Allow some timing variance due to thread scheduling
        self.assertGreater(after_second - after_first, 0.15)

    @patch("versiontracker.apps.is_homebrew_available")
    def test_get_homebrew_casks_list_no_homebrew(self, mock_is_homebrew):
        """Test get_homebrew_casks_list when Homebrew is not available."""
        # Mock is_homebrew_available to return False
        mock_is_homebrew.return_value = False
        
        # Call the function
        result = get_homebrew_casks_list()
        
        # Verify an empty list is returned
        self.assertEqual(result, [])

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    def test_get_homebrew_casks_list_cached(self, mock_read_cache, mock_is_homebrew):
        """Test get_homebrew_casks_list with cached data."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return cached cask list
        mock_read_cache.return_value = {"casks": ["firefox", "chrome"]}
        
        # Call the function
        result = get_homebrew_casks_list()
        
        # Verify the cached value is returned
        self.assertEqual(result, ["firefox", "chrome"])

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps.run_command")
    @patch("versiontracker.apps.write_cache")
    def test_get_homebrew_casks_list_no_cache(
        self, mock_write_cache, mock_run_command, mock_read_cache, mock_is_homebrew
    ):
        """Test get_homebrew_casks_list without cached data."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return None (no cache)
        mock_read_cache.return_value = None
        
        # Mock run_command to return cask and formula lists
        mock_run_command.side_effect = [
            ("firefox\nchrome", 0),  # casks
            ("python\nnode", 0)      # formulas
        ]
        
        # Call the function
        result = get_homebrew_casks_list()
        
        # Verify the combined list is returned
        expected = ["firefox", "chrome", "python", "node"]
        self.assertEqual(result, expected)
        
        # Verify the cache was updated
        mock_write_cache.assert_called_once_with("brew_casks", {"casks": expected})

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_list_first_command_fails(
        self, mock_run_command, mock_read_cache, mock_is_homebrew
    ):
        """Test get_homebrew_casks_list when first brew command fails."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return None (no cache)
        mock_read_cache.return_value = None
        
        # Mock run_command to fail on first call, succeed on second and third
        mock_run_command.side_effect = [
            ("Error: invalid option", 1),  # First call fails
            ("firefox\nchrome", 0),        # Second call succeeds
            ("python\nnode", 0)            # Third call succeeds (formulas)
        ]
        
        # Call the function
        result = get_homebrew_casks_list()
        
        # Verify the combined list is returned
        expected = ["firefox", "chrome", "python", "node"]
        self.assertEqual(result, expected)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_list_all_commands_fail(
        self, mock_run_command, mock_read_cache, mock_is_homebrew
    ):
        """Test get_homebrew_casks_list when both brew commands fail."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return None (no cache)
        mock_read_cache.return_value = None
        
        # Mock run_command to fail on both calls
        mock_run_command.return_value = ("Error: command failed", 1)
        
        # Test that HomebrewError is raised
        with self.assertRaises(HomebrewError):
            get_homebrew_casks_list()

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_list_permission_error(
        self, mock_run_command, mock_read_cache, mock_is_homebrew
    ):
        """Test get_homebrew_casks_list with permission error."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return None (no cache)
        mock_read_cache.return_value = None
        
        # Mock run_command to raise BrewPermissionError
        mock_run_command.side_effect = BrewPermissionError("Permission denied")
        
        # Test that BrewPermissionError is re-raised
        with self.assertRaises(BrewPermissionError):
            get_homebrew_casks_list()

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_list_timeout(
        self, mock_run_command, mock_read_cache, mock_is_homebrew
    ):
        """Test get_homebrew_casks_list with timeout error."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return None (no cache)
        mock_read_cache.return_value = None
        
        # Mock run_command to raise BrewTimeoutError
        mock_run_command.side_effect = BrewTimeoutError("Operation timed out")
        
        # Test that BrewTimeoutError is re-raised
        with self.assertRaises(BrewTimeoutError):
            get_homebrew_casks_list()

    @patch("versiontracker.apps.is_homebrew_available")
    def test_is_brew_cask_installable_no_homebrew(self, mock_is_homebrew):
        """Test is_brew_cask_installable when Homebrew is not available."""
        # Mock is_homebrew_available to return False
        mock_is_homebrew.return_value = False
        
        # Call the function
        result = is_brew_cask_installable("firefox")
        
        # Verify False is returned
        self.assertFalse(result)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    def test_is_brew_cask_installable_cached(self, mock_read_cache, mock_is_homebrew):
        """Test is_brew_cask_installable with cached data."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return cached installable casks
        mock_read_cache.return_value = {"installable": ["firefox", "chrome"]}
        
        # Test with cask in cache
        self.assertTrue(is_brew_cask_installable("firefox"))
        
        # Test with cask not in cache
        with patch("versiontracker.apps.run_command") as mock_run_command:
            mock_run_command.return_value = ("No formulae or casks found", 1)
            self.assertFalse(is_brew_cask_installable("nonexistent"))

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps.run_command")
    @patch("versiontracker.apps.write_cache")
    def test_is_brew_cask_installable_found(
        self, mock_write_cache, mock_run_command, mock_read_cache, mock_is_homebrew
    ):
        """Test is_brew_cask_installable when cask is found."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return None (empty cache)
        mock_read_cache.return_value = None
        
        # Mock run_command to return success
        mock_run_command.return_value = ("firefox", 0)
        
        # Call the function
        result = is_brew_cask_installable("firefox")
        
        # Verify True is returned
        self.assertTrue(result)
        
        # Verify the cache was updated
        mock_write_cache.assert_called_once()

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps.run_command")
    def test_is_brew_cask_installable_not_found(
        self, mock_run_command, mock_read_cache, mock_is_homebrew
    ):
        """Test is_brew_cask_installable when cask is not found."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return None (empty cache)
        mock_read_cache.return_value = None
        
        # Mock run_command to return not found error
        mock_run_command.return_value = ("No formulae or casks found", 1)
        
        # Call the function
        result = is_brew_cask_installable("nonexistent")
        
        # Verify False is returned
        self.assertFalse(result)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps.run_command")
    def test_is_brew_cask_installable_network_error(
        self, mock_run_command, mock_read_cache, mock_is_homebrew
    ):
        """Test is_brew_cask_installable with network error."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return None (empty cache)
        mock_read_cache.return_value = None
        
        # Mock run_command to raise NetworkError
        mock_run_command.side_effect = Exception("Temporary failure in name resolution")
        
        # Test that NetworkError is raised
        with self.assertRaises(NetworkError):
            is_brew_cask_installable("firefox")

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps.run_command")
    def test_is_brew_cask_installable_timeout(
        self, mock_run_command, mock_read_cache, mock_is_homebrew
    ):
        """Test is_brew_cask_installable with timeout error."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True
        
        # Mock read_cache to return None (empty cache)
        mock_read_cache.return_value = None
        
        # Mock run_command to raise BrewTimeoutError
        mock_run_command.side_effect = BrewTimeoutError("Operation timed out")
        
        # Test that BrewTimeoutError is re-raised
        with self.assertRaises(BrewTimeoutError):
            is_brew_cask_installable("firefox")


if __name__ == "__main__":
    unittest.main()
