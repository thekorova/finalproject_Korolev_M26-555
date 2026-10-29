from functools import wraps

from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import logger


def log_action(command, verbose=False):
    """Сохраняет результат функции в лог"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            container = {}
            kwargs["container"] = container
            user = args[0] if len(args) > 0 else kwargs.get("user")
            currency_code = args[1] if len(args) > 1 else kwargs.get("currency_code")
            amount = args[2] if len(args) > 2 else kwargs.get("amount")
            settings = SettingsLoader()
            base = settings.get("base_currency")
            try:
                result = func(*args, **kwargs)
            except Exception as error:
                rate = container.get("rate")
                logger.info(
                    "%s user='%s' currency='%s' amount=%s rate=%s base='%s' "
                    "result=ERROR error_type=%s error_message=%s",
                    command,
                    getattr(user, "username", None),
                    currency_code,
                    amount,
                    rate,
                    base,
                    type(error).__name__,
                    str(error),
                )
                raise
            rate = container.get("rate")
            logger.info(
                "%s user='%s' currency='%s' amount=%s rate=%s base='%s' result=OK",
                command,
                getattr(user, "username", None),
                currency_code,
                amount,
                rate,
                base,
            )
            if verbose:
                logger.info(
                    "%s balance_before=%.4f balance_after=%.4f",
                    command,
                    container.get("balance_before"),
                    container.get("balance_after"),
                )
            return result

        return wrapper

    return decorator
