import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError, InsufficientFundsError
from valutatrade_hub.core.models import PASSWORD_ITERATIONS, Portfolio, User
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service import storage
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.updater import RatesUpdater


def register_user(username, password):
    """Регистрирует нового пользователя и создает пустой портфель"""
    settings = SettingsLoader()
    db = DatabaseManager()
    if not isinstance(username, str):
        raise TypeError("Имя пользователя должно быть строкой")
    username = username.strip()
    if not username:
        raise ValueError("Имя пользователя не может быть пустым")
    if not isinstance(password, str):
        raise TypeError("Пароль должен быть строкой")
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")
    users = db.load(settings.get("users_path"), [])
    for user in users:
        if user["username"] == username:
            raise ValueError(f"Имя пользователя '{username}' уже занято")
    user_id = 1
    for i in users:
        if i["user_id"] >= user_id:
            user_id = i["user_id"] + 1
    salt_bytes = secrets.token_bytes(16)
    hashed_password = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_bytes, PASSWORD_ITERATIONS
    )
    new_user = User(
        user_id,
        username,
        hashed_password.hex(),
        salt_bytes.hex(),
        datetime.now(),
    )
    user_data = {
        "user_id": new_user.user_id,
        "username": new_user.username,
        "hashed_password": new_user.hashed_password,
        "salt": new_user.salt,
        "registration_date": new_user.registration_date.isoformat(),
    }
    users.append(user_data)
    db.save(settings.get("users_path"), users)
    portfolios = db.load(settings.get("portfolios_path"), [])
    portfolios.append({"user_id": new_user.user_id, "wallets": {}})
    db.save(settings.get("portfolios_path"), portfolios)
    return (
        f"Пользователь '{username}' зарегистрирован (id={user_id}). "
        f"Войдите: login --username {username} --password {'*' * len(password)}"
    )


def login_user(username, password):
    """Проверяет имя пользователя и пароль"""
    settings = SettingsLoader()
    db = DatabaseManager()
    users = db.load(settings.get("users_path"), [])
    user_data = next((i for i in users if i["username"] == username), None)
    if user_data is None:
        raise ValueError(f"Пользователь '{username}' не найден")
    user = User(
        user_data["user_id"],
        user_data["username"],
        user_data["hashed_password"],
        user_data["salt"],
        datetime.fromisoformat(user_data["registration_date"]),
    )
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")
    return user


def get_user_portfolio(user: User):
    """Загружает портфель пользователя из json"""
    settings = SettingsLoader()
    db = DatabaseManager()
    portfolios = db.load(settings.get("portfolios_path"), [])
    portfolio_data = next((i for i in portfolios if i["user_id"] == user.user_id), None)
    if portfolio_data is None:
        raise ValueError("Портфель пользователя не найден")
    portfolio = Portfolio(user)
    for k, v in portfolio_data["wallets"].items():
        portfolio.add_currency(k)
        portfolio.get_wallet(k).balance = v["balance"]
    return portfolio


def save_user_portfolio(portfolio: Portfolio):
    """Сохраняет портфель пользователя в json"""
    settings = SettingsLoader()
    db = DatabaseManager()
    portfolios = db.load(settings.get("portfolios_path"), [])
    portfolio_data = next(
        (i for i in portfolios if i["user_id"] == portfolio.user.user_id), None
    )
    wallets = {}
    for k, v in portfolio.wallets.items():
        wallets[k] = {"balance": v.balance}
    if portfolio_data is None:
        portfolios.append(
            {
                "user_id": portfolio.user.user_id,
                "wallets": wallets,
            }
        )
    else:
        portfolio_data["wallets"] = wallets
    db.save(settings.get("portfolios_path"), portfolios)


def get_cached_rates():
    """Загружает сохранённые курсы валют из json"""
    settings = SettingsLoader()
    db = DatabaseManager()
    return db.load(settings.get("rates_path"), {})


def get_exchange_rates(currency_code=None):
    """Возвращает актуальные курсы валют относительно базовой валюты"""
    settings = SettingsLoader()
    base = settings.get("base_currency")
    pairs = get_cached_rates().get("pairs", {})
    rates = {base: 1.0}
    if currency_code is not None:
        pair = f"{currency_code}_{base}"
        data = pairs.get(pair)
        if data is None or not rate_refresh(data["updated_at"]):
            refresh_rate()
            pairs = get_cached_rates().get("pairs", {})
            data = pairs.get(pair)
        if data is None or not rate_refresh(data["updated_at"]):
            raise ApiRequestError(f"Не удалось получить актуальный курс {pair}")
    for k, v in pairs.items():
        if not k.endswith(f"_{base}"):
            continue
        if not rate_refresh(v["updated_at"]):
            continue
        code = k.split("_")[0]
        rates[code] = v["rate"]
    return rates


@log_action("BUY", verbose=True)
def buy_currency(user: User, currency_code, amount, container=None):
    """Покупает валюту за USD и сохраняет изменения портфеля"""
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise TypeError("'amount' должен быть числом")
    if not amount > 0:
        raise ValueError("'amount' должен быть положительным числом")
    if not isinstance(currency_code, str):
        raise TypeError("'currency_code' должен быть строкой")
    currency_code = currency_code.strip().upper()
    get_currency(currency_code)
    if not currency_code:
        raise ValueError("'currency_code' не может быть пустым")
    if currency_code == "USD":
        raise ValueError("Нельзя покупать USD за USD")
    rates = get_exchange_rates(currency_code)
    if currency_code not in rates:
        raise ValueError(f"Не удалось получить курс для {currency_code}→USD")
    rate = rates[currency_code]
    if container is not None:
        container["rate"] = rate
    cost_usd = amount * rate
    portfolio = get_user_portfolio(user)
    try:
        usd_wallet = portfolio.get_wallet("USD")
    except KeyError as error:
        raise ValueError("У пользователя нет USD-кошелька") from error
    if not cost_usd > 0:
        raise ValueError("Некорректная стоимость покупки")
    if cost_usd > usd_wallet.balance:
        raise InsufficientFundsError(usd_wallet.balance, cost_usd, "USD")
    if currency_code not in portfolio.wallets:
        portfolio.add_currency(currency_code)
    currency_wallet = portfolio.get_wallet(currency_code)
    old_balance = currency_wallet.balance
    new_balance = old_balance + amount
    if not new_balance > old_balance:
        raise ValueError("Некорректный баланс после покупки")
    if container is not None:
        container["balance_before"] = currency_wallet.balance
    usd_wallet.withdraw(cost_usd)
    currency_wallet.deposit(amount)
    if container is not None:
        container["balance_after"] = currency_wallet.balance
    save_user_portfolio(portfolio)
    return (
        f"Покупка выполнена: {amount:.4f} {currency_code} "
        f"по курсу {rate:.2f} USD/{currency_code}\n"
        f"Изменения в портфеле:\n"
        f"- {currency_code}: было {old_balance:.4f} "
        f"→ стало {currency_wallet.balance:.4f}\n"
        f"Оценочная стоимость покупки: {cost_usd:,.2f} USD"
    )


def rate_refresh(updated_at):
    """Проверяет, актуальность курса по ТТЛ из настроек"""
    settings = SettingsLoader()
    ttl = settings.get("rates_ttl_seconds")
    updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if timedelta(0) <= now - updated_at < timedelta(seconds=ttl):
        return True
    else:
        return False


@log_action("SELL", verbose=True)
def sell_currency(user: User, currency_code, amount, container=None):
    """Продает валюту за USD и сохраняет изменения портфеля."""
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise TypeError("'amount' должен быть числом")
    if not amount > 0:
        raise ValueError("'amount' должен быть положительным числом")
    if not isinstance(currency_code, str):
        raise TypeError("'currency_code' должен быть строкой")
    currency_code = currency_code.strip().upper()
    if not currency_code:
        raise ValueError("'currency_code' не может быть пустым")
    get_currency(currency_code)
    if currency_code == "USD":
        raise ValueError("Нельзя продавать USD за USD")
    rates = get_exchange_rates(currency_code)
    if currency_code not in rates:
        raise ValueError(f"Не удалось получить курс для {currency_code}→USD")
    portfolio = get_user_portfolio(user)
    try:
        currency_wallet = portfolio.get_wallet(currency_code)
    except KeyError as error:
        raise InsufficientFundsError(0, amount, currency_code) from error
    if amount > currency_wallet.balance:
        raise InsufficientFundsError(currency_wallet.balance, amount, currency_code)
    if "USD" not in portfolio.wallets:
        portfolio.add_currency("USD")
    usd_wallet = portfolio.get_wallet("USD")
    rate = rates[currency_code]
    if container is not None:
        container["rate"] = rate
    revenue_usd = amount * rate
    old_balance = currency_wallet.balance
    if container is not None:
        container["balance_before"] = currency_wallet.balance
    currency_wallet.withdraw(amount)
    usd_wallet.deposit(revenue_usd)
    if container is not None:
        container["balance_after"] = currency_wallet.balance
    save_user_portfolio(portfolio)
    return (
        f"Продажа выполнена: {amount:.4f} {currency_code} "
        f"по курсу {rate:.2f} USD/{currency_code}\n"
        f"Изменения в портфеле:\n"
        f"- {currency_code}: было {old_balance:.4f} "
        f"→ стало {currency_wallet.balance:.4f}\n"
        f"Оценочная выручка: {revenue_usd:,.2f} USD"
    )


def refresh_rate():
    """Обновляет курсы валют через Parser Service"""
    clients = [CoinGeckoClient(), ExchangeRateApiClient()]
    updater = RatesUpdater(clients=clients, storage=storage)
    updater.run_update()


def get_currency_rate(from_currency, to_currency):
    """Возвращает курс одной валюты относительно другой."""
    if not isinstance(from_currency, str):
        raise TypeError("'from_currency' должен быть строкой")
    if not isinstance(to_currency, str):
        raise TypeError("'to_currency' должен быть строкой")
    from_currency = from_currency.strip().upper()
    to_currency = to_currency.strip().upper()
    if not from_currency:
        raise ValueError("'from_currency' не может быть пустым")
    if not to_currency:
        raise ValueError("'to_currency' не может быть пустым")
    get_currency(from_currency)
    get_currency(to_currency)
    settings = SettingsLoader()
    base = settings.get("base_currency")
    cached_rates = get_cached_rates()
    rates = cached_rates.get("pairs", {})
    for i in [from_currency, to_currency]:
        if i == base:
            continue
        pair = f"{i}_{base}"
        data = rates.get(pair)
        if data is None or not rate_refresh(data["updated_at"]):
            refresh_rate()
            cached_rates = get_cached_rates()
            rates = cached_rates.get("pairs", {})
            data = rates.get(pair)
        if data is None or not rate_refresh(data["updated_at"]):
            raise ApiRequestError(
                f"Не удалось получить курс {from_currency}→{to_currency}"
            )
    if from_currency == base:
        from_rate = 1
    else:
        from_rate = rates[f"{from_currency}_{base}"]["rate"]
    if to_currency == base:
        to_rate = 1
    else:
        to_rate = rates[f"{to_currency}_{base}"]["rate"]
    rate = from_rate / to_rate
    re_rate = 1 / rate
    if rate < 1:
        rate_text = f"{rate:.8f}"
    else:
        rate_text = f"{rate:.2f}"
    if re_rate < 1:
        re_rate_text = f"{re_rate:.8f}"
    else:
        re_rate_text = f"{re_rate:.2f}"
    updated_at = cached_rates.get("last_refresh")
    if updated_at is not None:
        updated_at = updated_at.replace("T", " ")
    else:
        updated_at = "нет данных"
    return (
        f"Курс {from_currency}→{to_currency}: {rate_text} "
        f"(обновлено: {updated_at})\n"
        f"Обратный курс {to_currency}→{from_currency}: {re_rate_text}"
    )
