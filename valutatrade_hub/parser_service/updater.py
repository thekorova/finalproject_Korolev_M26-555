from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import logger
from valutatrade_hub.parser_service.api_clients import BaseApiClient


class RatesUpdater:
    """Координирует обновление курсов валют"""

    def __init__(self, clients: list[BaseApiClient], storage):
        self.clients = clients
        self.storage = storage
        self.errors = []
        self.last_refresh = None

    def run_update(self):
        all_rates = {}
        self.errors = []
        self.last_refresh = None
        logger.info("Starting rates update...")
        time_upd = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        for i in self.clients:
            try:
                rates = i.fetch_rates()
                for k, v in rates.items():
                    all_rates[k] = {
                        "rate": v,
                        "updated_at": time_upd,
                        "source": i.source,
                    }
                logger.info("Fetching from %s... OK (%s rates)", i.source, len(rates))
            except ApiRequestError as error:
                logger.error("Failed to fetch from %s: %s", i.source, error)
                self.errors.append(str(error))
                continue
        if not all_rates:
            raise ApiRequestError("Не удалось получить курсы по всем API")
        end_dict = {"pairs": all_rates, "last_refresh": time_upd}
        logger.info("Writing %s rates to data/rates.json...", len(all_rates))
        rates_count = self.storage.save_rates(end_dict)
        self.last_refresh = time_upd
        return rates_count
