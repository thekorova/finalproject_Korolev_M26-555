class InsufficientFundsError(ValueError):
    """Ошибка недостатка средств."""

    def __init__(self, available, required, code):
        self.available = available
        self.required = required
        self.code = code
        super().__init__(
            f"Недостаточно средств: доступно {available} "
            f"{code}, требуется {required} {code}"
        )


class CurrencyNotFoundError(ValueError):
    """Ошибка неизвестной валюты."""

    def __init__(self, code):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(Exception):
    """Ошибка обращения к внешнему API."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
