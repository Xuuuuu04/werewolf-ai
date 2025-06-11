import logging
import json


class Log():
    def __init__(self, viewer, source, target, content, day, time, event):
        self.viewer = viewer
        self.source = source
        self.target = target
        self.content = content
        self.day = day
        self.time = time
        self.event = event


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = record.__dict__.copy()
        non_custom_fields = [
            'name', 'msg', 'args', 'levelname', 'levelno',
            'pathname', 'filename', 'module', 'exc_info',
            'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread',
            'threadName', 'processName', 'process', 'message',
        ]
        for field in non_custom_fields:
            if field in log_record:
                del log_record[field]

        log_record['message'] = record.getMessage()
        return json.dumps(log_record, ensure_ascii=False)


class CustomLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        return msg, kwargs

