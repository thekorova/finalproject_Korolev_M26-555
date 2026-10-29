import shlex

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


def get_argument(command, arg):
    """Возвращает значение аргумента команды."""
    if arg not in command:
        raise ValueError(f"Не указан аргумент {arg}")
    index = command.index(arg)
    if index + 1 >= len(command) or command[index + 1].startswith("--"):
        raise ValueError(f"Не указано значение для {arg}")
    return command[index + 1]


def main():
    """Запускает командный интерфейс."""
    current_user = None
    print("ValutaTrade Hub")
    print("Введите команду:")
    while True:
        try:
            command = shlex.split(input("> ").strip())
            if not command:
                continue
            match command[0]:
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
