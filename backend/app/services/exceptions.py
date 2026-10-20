class ApplicationError(Exception):
    code = "APPLICATION_ERROR"
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DuplicateRecordError(ApplicationError):
    code = "DUPLICATE_RECORD"
    status_code = 409


class RecordNotFoundError(ApplicationError):
    code = "RECORD_NOT_FOUND"
    status_code = 404


class InvalidSessionError(ApplicationError):
    code = "INVALID_SESSION"
    status_code = 400


class InvalidOperationError(ApplicationError):
    code = "INVALID_OPERATION"
    status_code = 409

