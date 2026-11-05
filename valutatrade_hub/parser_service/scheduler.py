import logging
import time

from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service import storage
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.updater import RatesUpdater


def scheduler():
    """Периодически обновляет курсы валют"""
    settings = SettingsLoader()
    interval = settings.get("rates_ttl_seconds")
    clients = [CoinGeckoClient(), ExchangeRateApiClient()]
    updater = RatesUpdater(clients, storage)
    logger = logging.getLogger("valutatrade")

    while True:
        try:
            updater.run_update()
        except Exception:
            logger.exception("Ошибка автоматического обновления курсов")
        time.sleep(interval)
