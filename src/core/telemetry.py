import os
import logging

logger = logging.getLogger(__name__)

def init_telemetry():
    """
    Initializes Sentry telemetry if SENTRY_DSN is present.
    """
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )

        sentry_sdk.init(
            dsn=dsn,
            integrations=[sentry_logging],
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            traces_sample_rate=1.0,
            # Set profiles_sample_rate to 1.0 to profile 100%
            # of transactions.
            profiles_sample_rate=1.0,
        )
        logger.info("Sentry telemetry initialized.")
    except ImportError:
        logger.warning("sentry-sdk not installed, skipping telemetry initialization.")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
