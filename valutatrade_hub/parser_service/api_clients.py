from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Унифицированный интерфейс для получения курсов."""

    @abstractmethod
    def fetch_rates(self) -> dict:
        """Получает курсы валют из внешнего API"""
        pass


class CoinGeckoClient(BaseApiClient):
    """Получает курсы криптовалют из CoinGecko"""

    def __init__(self):
        config = ParserConfig()
        self.coingecko_url = config.COINGECKO_URL
        self.crypto_id_map = config.CRYPTO_ID_MAP
        self.request_timeout = config.REQUEST_TIMEOUT
        self.base_currency = config.BASE_CURRENCY
        self.source = "CoinGecko"

    def fetch_rates(self) -> dict:
        ids = ",".join(self.crypto_id_map.values())
        params = {"ids": ids, "vs_currencies": self.base_currency.lower()}
        try:
            reply = requests.get(
                self.coingecko_url, params=params, timeout=self.request_timeout
            )
            reply.raise_for_status()
            data = reply.json()
        except requests.exceptions.RequestException as error:
            raise ApiRequestError(f"Ошибка CoinGecko: {error}") from error
        result = {}
        for k, v in self.crypto_id_map.items():
            rate = data[v][self.base_currency.lower()]
            result[f"{k}_{self.base_currency}"] = rate
        return result


class ExchangeRateApiClient(BaseApiClient):
    """Приводит данные к тому же стандартизированному
    формату и обрабатывает ошибки"""

    def __init__(self):
        config = ParserConfig()
        self.exchangerate_api_url = config.EXCHANGERATE_API_URL
        self.api_key = config.EXCHANGERATE_API_KEY
        self.base_currency = config.BASE_CURRENCY
        self.fiat_currencies = config.FIAT_CURRENCIES
        self.request_timeout = config.REQUEST_TIMEOUT
        self.source = "ExchangeRate-API"

    def fetch_rates(self) -> dict:
        url = f"{self.exchangerate_api_url}/{self.api_key}/latest/{self.base_currency}"
        try:
            reply = requests.get(url, timeout=self.request_timeout)
            reply.raise_for_status()
            data = reply.json()
        except requests.exceptions.RequestException as error:
            raise ApiRequestError(f"Ошибка ExchangeRate-API: {error}") from error
        if data.get("result") != "success":
            raise ApiRequestError(
                f"Ошибка ExchangeRate-API: "
                f"{data.get('error-type', 'неизвестная ошибка')}"
            )
        rates = data["conversion_rates"]
        result = {}
        for i in self.fiat_currencies:
            rate = rates[i]
            result[f"{i}_{self.base_currency}"] = 1 / rate
        return result
