# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt


class SimulatorException(Exception):
    """Base exception for simulator errors"""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


class ServerException(SimulatorException):
    """Errors related to server operations"""

    pass


class DatastoreException(SimulatorException):
    """Errors related to datastore operations"""

    pass


class SignalException(SimulatorException):
    """Errors related to signal operations"""

    pass


class ScriptException(SimulatorException):
    """Errors related to script execution"""

    pass


class StatusException(SimulatorException):
    """Errors related to status management"""

    pass


class ValidationException(SimulatorException):
    """Errors related to validation"""

    pass
