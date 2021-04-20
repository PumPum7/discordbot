from loguru import logger

LOG = None


class Log:
    def __init__(self):
        global LOG
        if not LOG:
            LOG = self.start_logger(logger)
        self.logging = LOG

    def start_logger(self, logger_):
        # start_logger: add all needed loggers
        logger_.add("data/logs/logs_debug.log", rotation="500 MB", compression="zip", level="DEBUG", backtrace=True,
                    format="time={time:YYYY-MM-DD HH:mm:ss} level={level} msg={message}", filter=self._only_debug)
        logger_.add("data/logs/logs_info.log", rotation="500 MB", compression="zip", level="INFO",
                    format="time={time:YYYY-MM-DD HH:mm:ss} level={level} msg={message}", filter=self._only_info)
        logger_.add("data/logs/logs_error.log", rotation="500 MB", compression="zip", level="ERROR", backtrace=True,
                    format="time={time:YYYY-MM-DD HH:mm:ss} level={level} msg={message}", filter=self._only_error)
        # remove the stdout logger
        logger_.remove(handler_id=0)
        return logger

    @staticmethod
    def _only_info(record):
        # _only_info: filter the results to only include info logs
        return record["level"].name == "INFO"

    @staticmethod
    def _only_debug(record):
        # _only_debug: filter the results to only include debug logs
        return record["level"].name == "DEBUG"

    @staticmethod
    def _only_error(record):
        # _only_error: filter the results to only include error logs
        return record["level"].name == "ERROR"
