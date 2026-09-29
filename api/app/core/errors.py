"""Public errors contain fixed messages, never provider bodies or credentials."""


class ServiceError(Exception):
    status_code = 500
    code = "internal_error"
    message = "Không thể xử lý yêu cầu."

    def __init__(self) -> None:
        super().__init__(self.message)


class ProviderError(ServiceError):
    status_code = 502
    code = "provider_error"
    message = "Dịch vụ AI không khả dụng hoặc trả dữ liệu không hợp lệ."

    def __init__(self, *, retryable: bool = False) -> None:
        self.retryable = retryable
        super().__init__()


class InvalidDocument(ServiceError):
    status_code = 422
    code = "invalid_document"
    message = "Tài liệu trống, không hợp lệ hoặc không có nội dung văn bản."


class PolicyBlocked(ProviderError):
    status_code = 422
    code = "policy_blocked"
    message = "Nội dung bị chặn bởi chính sách bảo mật. Hãy thử câu hỏi khác."


class BudgetExceeded(ProviderError):
    status_code = 429
    code = "budget_exceeded"
    message = "Ngân sách AI của workload đã hết. Liên hệ người quản lý lab."


class GuardrailUnavailable(ProviderError):
    status_code = 503
    code = "guardrail_unavailable"
    message = "Kiểm tra bảo mật đang không khả dụng. Vui lòng thử lại sau."


class DocumentNotFound(ServiceError):
    status_code = 404
    code = "document_not_found"
    message = "Không tìm thấy tài liệu."


class DocumentConflict(ServiceError):
    status_code = 409
    code = "document_conflict"
    message = "Document ID đã gắn với nội dung hoặc cấu hình xử lý khác."


class IndexIdentityConflict(ServiceError):
    status_code = 409
    code = "index_identity_conflict"
    message = (
        "Embedding identity không khớp index. Cần rebuild index bằng cấu hình đã chọn."
    )


class SchemaMismatch(ServiceError):
    status_code = 503
    code = "schema_mismatch"
    message = "Schema chưa sẵn sàng hoặc dimension không khớp EMBEDDING_DIM."


class QueueUnavailable(ServiceError):
    status_code = 503
    code = "queue_unavailable"
    message = "Hàng đợi xử lý chưa sẵn sàng. Vui lòng thử lại sau."
