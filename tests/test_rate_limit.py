import pytest
import time
from unittest.mock import MagicMock, patch
from src.utils.rate_limit import with_backoff

def test_with_backoff_success():
    """Test that the decorator returns the result of a successful function call."""
    mock_func = MagicMock(return_value="success")
    mock_func.__name__ = "mock_func"
    decorated_func = with_backoff()(mock_func)
    
    result = decorated_func()
    
    assert result == "success"
    assert mock_func.call_count == 1

def test_with_backoff_retry_then_success():
    """Test that the decorator retries and eventually succeeds."""
    mock_func = MagicMock()
    mock_func.__name__ = "mock_func"
    mock_func.side_effect = [ValueError("fail"), "success"]
    
    # Patch time.sleep to avoid actual delays in tests
    with patch("time.sleep") as mock_sleep:
        decorated_func = with_backoff(exceptions=(ValueError,))(mock_func)
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2
        assert mock_sleep.call_count == 1

def test_with_backoff_max_retries_exceeded():
    """Test that the decorator raises the exception after max retries are exceeded."""
    mock_func = MagicMock(side_effect=ValueError("persistent fail"))
    mock_func.__name__ = "mock_func"
    
    with patch("time.sleep") as mock_sleep:
        decorated_func = with_backoff(max_retries=3, exceptions=(ValueError,))(mock_func)
        
        with pytest.raises(ValueError, match="persistent fail"):
            decorated_func()
            
        assert mock_func.call_count == 4  # Initial call + 3 retries
        assert mock_sleep.call_count == 3

def test_with_backoff_unhandled_exception():
    """Test that the decorator does not retry for unhandled exceptions."""
    mock_func = MagicMock(side_effect=KeyError("unhandled"))
    mock_func.__name__ = "mock_func"
    
    decorated_func = with_backoff(exceptions=(ValueError,))(mock_func)
    
    with pytest.raises(KeyError, match="unhandled"):
        decorated_func()
        
    assert mock_func.call_count == 1

def test_with_backoff_delay_calculation():
    """Test that the delay increases exponentially and respects max_delay."""
    mock_func = MagicMock(side_effect=[ValueError("fail")] * 5 + ["success"])
    mock_func.__name__ = "mock_func"
    
    base_delay = 1.0
    max_delay = 5.0
    
    with patch("time.sleep") as mock_sleep, patch("random.uniform", return_value=0.0):
        decorated_func = with_backoff(
            max_retries=10, 
            base_delay=base_delay, 
            max_delay=max_delay, 
            exceptions=(ValueError,)
        )(mock_func)
        
        decorated_func()
        
        # Expected delays (without jitter):
        # Retry 1: min(1.0 * 2^0, 5.0) = 1.0
        # Retry 2: min(1.0 * 2^1, 5.0) = 2.0
        # Retry 3: min(1.0 * 2^2, 5.0) = 4.0
        # Retry 4: min(1.0 * 2^3, 5.0) = 5.0
        # Retry 5: min(1.0 * 2^4, 5.0) = 5.0
        
        expected_calls = [1.0, 2.0, 4.0, 5.0, 5.0]
        actual_calls = [call.args[0] for call in mock_sleep.call_args_list]
        
        assert actual_calls == expected_calls

def test_with_backoff_jitter():
    """Test that jitter is added to the delay."""
    mock_func = MagicMock(side_effect=[ValueError("fail"), "success"])
    mock_func.__name__ = "mock_func"
    
    with patch("time.sleep") as mock_sleep, patch("random.uniform", return_value=0.5):
        decorated_func = with_backoff(base_delay=1.0, exceptions=(ValueError,))(mock_func)
        decorated_func()
        
        # Delay = 1.0, Jitter = 0.5, Total = 1.5
        mock_sleep.assert_called_once_with(1.5)
