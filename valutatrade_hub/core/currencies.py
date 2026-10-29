import math
from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс валюты."""

    def __init__(self, name: str, code: str):
        if not isinstance(name, str):
            raise TypeError("Название валюты должно быть строкой")
        if not name.strip():
            raise ValueError("Название валюты не может быть пустым")
        if not isinstance(code, str):
            raise TypeError("Код валюты должен быть строкой")
        if not 2 <= len(code) <= 5:
            raise ValueError("Код валюты должен содержать от 2 до 5 символов")
        if not code.isalpha() or not code.isascii() or not code.isupper():
            raise ValueError("Код валюты должен содержать заглавные латинские буквы")
        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает информацию о валюте"""
        pass


class FiatCurrency(Currency):
    """Описывает фиатную валюту."""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        if not isinstance(issuing_country, str):
            raise TypeError("Страна эмиссии должна быть строкой")
        if not issuing_country.strip():
            raise ValueError("Страна эмиссии не может быть пустой")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        """Возвращает информацию о фиатной валюте"""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Описывает криптовалюту."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)
        if not isinstance(algorithm, str):
            raise TypeError("Алгоритм должен быть строкой")
        if not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")
        if isinstance(market_cap, bool) or not isinstance(market_cap, (int, float)):
            raise TypeError("Капитализация должна быть числом")
        if not math.isfinite(market_cap):
            raise ValueError("Капитализация должна быть конечным числом")
        if market_cap < 0:
            raise ValueError("Капитализация не может быть отрицательной")
        self.algorithm = algorithm.strip()
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        """Возвращает информацию о криптовалюте"""
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


currencies = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Proof of Stake", 4.0e11),
}


def get_currency(code: str) -> Currency:
    """Возвращает объект валюты по коду."""
    if not isinstance(code, str):
        raise TypeError("Код валюты должен быть строкой")
    code = code.strip().upper()
    if code not in currencies:
        raise CurrencyNotFoundError(code)
    return currencies[code]
