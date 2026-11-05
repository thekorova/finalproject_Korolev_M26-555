import math
from datetime import datetime

from valutatrade_hub.core.utils import load_json, save_json
from valutatrade_hub.parser_service.config import ParserConfig

config = ParserConfig()


def load_rates():
    """Загружает текущие курсы"""
    return load_json(config.RATES_FILE_PATH, {"pairs": {}, "last_refresh": None})


def load_history():
    """Загружает историю курсов"""
    return load_json(config.HISTORY_FILE_PATH, {})


def save_rates(data):
    """Сохраняет курсы и историю измерений."""
    if not data["pairs"]:
        return 0
    cache = load_rates()
    history = load_history()
    rates_count = 0
    for k, v in data["pairs"].items():
        rate = v["rate"]
        time_upd = v["updated_at"]
        source = v["source"]
        if type(rate) not in (int, float) or rate <= 0 or not math.isfinite(rate):
            raise ValueError(f"Некорректный курс: {k}")
        codes = k.split("_")
        if len(codes) != 2:
            raise ValueError(f"Некорректная валютная пара: {k}")
        for code in codes:
            if code != code.upper():
                raise ValueError(f"Некорректный код валюты: {code}")
            if len(code) < 2 or len(code) > 5:
                raise ValueError(f"Некорректная длина кода: {code}")
        new_time = datetime.fromisoformat(time_upd.replace("Z", "+00:00"))
        record_id = f"{k}_{time_upd}"
        if record_id not in history:
            history[record_id] = {
                "id": record_id,
                "from_currency": codes[0],
                "to_currency": codes[1],
                "rate": rate,
                "timestamp": time_upd,
                "source": source,
                "meta": {},
            }
        old = cache["pairs"].get(k)
        if old is None:
            cache["pairs"][k] = v
            rates_count += 1
        else:
            old_time = datetime.fromisoformat(old["updated_at"].replace("Z", "+00:00"))
            if new_time > old_time:
                cache["pairs"][k] = v
                rates_count += 1
    cache["last_refresh"] = data["last_refresh"]
    save_json(config.HISTORY_FILE_PATH, history)
    save_json(config.RATES_FILE_PATH, cache)
    return rates_count
