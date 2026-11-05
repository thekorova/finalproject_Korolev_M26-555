import shlex
from threading import Thread

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import (
    buy_currency,
    get_currency_rate,
    get_exchange_rates,
    get_user_portfolio,
    login_user,
    register_user,
    sell_currency,
)
from valutatrade_hub.parser_service import storage
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.scheduler import scheduler
from valutatrade_hub.parser_service.updater import RatesUpdater


def get_argument(command, arg):
    """Возвращает значение аргумента команды."""
    if arg not in command:
        raise ValueError(f"Не указан аргумент {arg}")
    index = command.index(arg)
    if index + 1 >= len(command) or command[index + 1].startswith("--"):
        raise ValueError(f"Не указано значение для {arg}")
    return command[index + 1]


def show_help():
    """Выводит список доступных команд"""
    print("ValutaTrade Hub")
    print("Доступные команды:")
    print("Просмотр списка доступных команд")
    print("help")
    print("Регистрация пользователя")
    print("register --username <имя> --password <пароль>")
    print("Авторизация пользователя")
    print("login --username <имя> --password <пароль>")
    print("Просмотр портфеля пользователя")
    print("show-portfolio [--base <валюта>]")
    print("Покупка валюты")
    print("buy --currency <код> --amount <количество>")
    print("Продажа валюты")
    print("sell --currency <код> --amount <количество>")
    print("Получение курса валютной пары")
    print("get-rate --from <код> --to <код>")
    print("Обновление курсов из внешних API")
    print("update-rates [--source <coingecko|exchangerate>]")
    print("Просмотр курсов из локального кеша")
    print("show-rates [--currency <код>] [--top <число>] [--base <валюта>]")
    print("Завершение работы")
    print("exit")
    print("<...> — обязательные аргументы, [...] — необязательные")


def main():
    """Запускает командный интерфейс."""
    current_user = None
    config = ParserConfig()
    show_help()
    thread = Thread(target=scheduler, daemon=True)
    thread.start()
    print("Введите команду:")
    while True:
        try:
            command = shlex.split(input("> ").strip())
            if not command:
                continue
            match command[0]:
                case "help":
                    show_help()
                case "register":
                    username = get_argument(command, "--username")
                    password = get_argument(command, "--password")
                    print(register_user(username, password))
                case "login":
                    username = get_argument(command, "--username")
                    password = get_argument(command, "--password")
                    current_user = login_user(username, password)
                    print(f"Вы вошли как '{current_user.username}'")
                case "show-portfolio":
                    if current_user is None:
                        raise ValueError("Сначала выполните login")
                    base_currency = "USD"
                    if "--base" in command:
                        base_currency = get_argument(command, "--base").strip().upper()
                    portfolio = get_user_portfolio(current_user)
                    rates = get_exchange_rates()
                    if base_currency not in rates:
                        raise ValueError(
                            f"Неизвестная базовая валюта '{base_currency}'"
                        )
                    if not portfolio.wallets:
                        print("В вашем портфеле пока нет кошельков")
                        continue
                    print(
                        f"Портфель пользователя '{current_user.username}' "
                        f"(база: {base_currency}):"
                    )
                    for k, v in portfolio.wallets.items():
                        value = v.balance * rates[k] / rates[base_currency]
                        print(f"{k}: {v.balance:.4f} → {value:.2f} {base_currency}")
                    total = portfolio.get_total_value(rates, base_currency)
                    print(f"ИТОГО: {total:.2f} {base_currency}")
                case "buy":
                    if current_user is None:
                        raise ValueError("Сначала выполните login")
                    currency_code = get_argument(command, "--currency")
                    amount = get_argument(command, "--amount")
                    try:
                        amount = float(amount)
                    except ValueError as error:
                        raise ValueError(
                            "'amount' должен быть положительным числом"
                        ) from error
                    print(buy_currency(current_user, currency_code, amount))
                case "sell":
                    if current_user is None:
                        raise ValueError("Сначала выполните login")
                    currency_code = get_argument(command, "--currency")
                    amount = get_argument(command, "--amount")
                    try:
                        amount = float(amount)
                    except ValueError as error:
                        raise ValueError(
                            "'amount' должен быть положительным числом"
                        ) from error
                    print(sell_currency(current_user, currency_code, amount))
                case "get-rate":
                    from_currency = get_argument(command, "--from")
                    to_currency = get_argument(command, "--to")
                    print(get_currency_rate(from_currency, to_currency))
                case "update-rates":
                    clients = [CoinGeckoClient(), ExchangeRateApiClient()]
                    if "--source" in command:
                        source = get_argument(command, "--source").lower()
                        if source == "coingecko":
                            clients = [CoinGeckoClient()]
                        elif source == "exchangerate":
                            clients = [ExchangeRateApiClient()]
                        else:
                            raise ValueError(f"Неизвестный источник: {source}")
                    updater = RatesUpdater(clients=clients, storage=storage)
                    try:
                        rates_count = updater.run_update()
                    except ApiRequestError as error:
                        print(f"Ошибка обновления курсов: {error}")
                        continue
                    if updater.errors:
                        print(
                            "Update completed with errors. "
                            "Check logs/actions.log for details."
                        )
                    else:
                        print(
                            f"Update successful. Total rates updated: {rates_count}. "
                            f"Last refresh: {updater.last_refresh}"
                        )
                case "show-rates":
                    data = storage.load_rates()
                    rates = data["pairs"]
                    if not rates:
                        print(
                            "Локальный кеш курсов пуст. "
                            "Выполните 'update-rates', чтобы загрузить данные."
                        )
                        continue
                    if "--currency" in command:
                        currency = get_argument(command, "--currency").upper()
                        rates = {
                            k: v
                            for k, v in rates.items()
                            if k.split("_")[0] == currency
                        }
                        if not rates:
                            print(f"Курс для '{currency}' не найден в кеше.")
                            continue
                    if "--top" in command:
                        top = int(get_argument(command, "--top"))
                        if top <= 0:
                            raise ValueError("--top должен быть положительным числом")
                        rates = {
                            k: v
                            for k, v in rates.items()
                            if k.split("_")[0] in config.CRYPTO_CURRENCIES
                        }
                        rates = dict(
                            sorted(
                                rates.items(), key=lambda x: x[1]["rate"], reverse=True
                            )[:top]
                        )
                    else:
                        rates = dict(sorted(rates.items()))
                    base = config.BASE_CURRENCY
                    if "--base" in command:
                        base = get_argument(command, "--base").upper()
                    if base != config.BASE_CURRENCY:
                        base_rate = data["pairs"].get(f"{base}_USD")
                        if base_rate is None:
                            print(f"Курс для '{base}' не найден в кеше.")
                            continue
                    print(f"Rates from cache (updated at {data['last_refresh']}):")
                    for k, v in rates.items():
                        rate = v["rate"]
                        currency = k.split("_")[0]
                        if base != "USD":
                            rate = rate / base_rate["rate"]
                        print(f"- {currency}_{base}: {rate:.5f}")
                case "exit":
                    print("ValutaTrade Hub завершило работу")
                    break
                case _:
                    print(f"Неизвестная команда: {command[0]}")
        except InsufficientFundsError as error:
            print(f"Ошибка: {error}")
        except CurrencyNotFoundError as error:
            print(f"Ошибка: {error}")
            print("Проверьте код валюты")
        except ApiRequestError as error:
            print(f"Ошибка: {error}")
            print("Повторите попытку позже")
        except (ValueError, TypeError) as error:
            print(f"Ошибка: {error}")
