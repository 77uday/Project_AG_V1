from core.logger import Logger


def test_logger_basic_info_does_not_crash():
    logger = Logger("test_logger")
    logger.info("Test message")


def test_logger_with_context():
    logger = Logger("test_logger_context")
    logger.info("Order created", order_id="ORD123", symbol="NIFTY")


def test_logger_with_correlation_id():
    logger = Logger("test_logger_cid")
    logger.set_correlation_id("CID-001")
    logger.info("Order filled", order_id="ORD123")
