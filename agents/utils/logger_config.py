import logging
import sys


def setup_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """Sets up a logger with console output."""
    console_handler = logging.StreamHandler(sys.stdout)  # Explicitly use stdout
    console_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.propagate = False

    for logger_name in logging.root.manager.loggerDict:
        if logger_name.startswith("agents."):
            module_logger = logging.getLogger(logger_name)
            module_logger.handlers.clear()
            module_logger.addHandler(console_handler)
            module_logger.setLevel(level)
            module_logger.propagate = False

    for module in ["httpx", "urllib3"]:
        mod_logger = logging.getLogger(module)
        mod_logger.setLevel(logging.WARNING)
        mod_logger.handlers.clear()
        mod_logger.addHandler(console_handler)
        mod_logger.propagate = False

    sys.stdout.flush()

    return logger
