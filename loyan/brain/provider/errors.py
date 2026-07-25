"""Provider 异常体系"""


class ProviderError(Exception):
    """Provider 基类异常"""


class AuthError(ProviderError):
    """认证失败（API Key 无效/过期）"""


class RateLimitError(ProviderError):
    """频率限制"""


class QuotaExceededError(ProviderError):
    """额度耗尽"""


class TimeoutError(ProviderError):
    """请求超时"""


class ModelNotAvailableError(ProviderError):
    """模型不可用（不存在或已下线）"""


class ProviderNotAvailableError(ProviderError):
    """Provider 不可用（网络/服务端错误）"""
