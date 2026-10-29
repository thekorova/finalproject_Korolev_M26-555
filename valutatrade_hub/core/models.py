import hashlib
import hmac
import math
import secrets
from datetime import datetime

from valutatrade_hub.core.exceptions import InsufficientFundsError

PASSWORD_ITERATIONS = 600000


class User:
    """Описывает пользователя системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        if type(user_id) is not int:
            raise TypeError("ID пользователя должен быть целым числом")
        if user_id <= 0:
            raise ValueError("ID пользователя должен быть положительным")
        self._user_id = user_id
        self.username = username
        if type(hashed_password) is not str:
            raise TypeError("hesh должен быть строковым значением")
        if len(bytes.fromhex(hashed_password)) != 32:
            raise ValueError("Некорректный hesh")
        self._hashed_password = hashed_password
        if type(salt) is not str:
            raise TypeError("Соль должна быть строковым значением")
        if len(bytes.fromhex(salt)) != 16:
            raise ValueError("Некорректная соль")
        self._salt = salt
        if not isinstance(registration_date, datetime):
            raise TypeError("Дата регистрации должна быть объектом datetime")
        self._registration_date = registration_date

    @property
    def user_id(self):
        """Геттер: возвращает ИД пользователя"""
        return self._user_id

    @property
    def username(self):
        """Геттер: возвращает имя пользователя"""
        return self._username

    @username.setter
    def username(self, value):
        """Сеттер: проверяет имя пользователя"""
        if not isinstance(value, str):
            raise TypeError("Имя пользователя должно быть строкой")
        if not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value

    @property
    def registration_date(self):
        """Геттер: возвращает дату регистрации пользователя."""
        return self._registration_date

    @property
    def hashed_password(self):
        """Геттер: возвращает сохраненный хеш"""
        return self._hashed_password

    @property
    def salt(self):
        """Геттер: возвращает сохраненную соль"""
        return self._salt

    def get_user_info(self):
        """Предоставляет информецию о пользователе"""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def verify_password(self, password):
        """Проверяет пароль пользователя."""
        if not isinstance(password, str):
            raise TypeError("Пароль должен быть строкой")
        salt_bytes = bytes.fromhex(self._salt)
        password = password.encode("utf-8")
        calculated_hash = hashlib.pbkdf2_hmac(
            "sha256", password, salt_bytes, PASSWORD_ITERATIONS
        )
        return hmac.compare_digest(
            calculated_hash, bytes.fromhex(self._hashed_password)
        )

    def change_password(self, new_password):
        """Изменяет пароль пользователя."""
        if not isinstance(new_password, str):
            raise TypeError("Пароль должен быть строкой")
        if len(new_password) < 4:
            raise ValueError("Пароль не должен быть короче 4 символов")
        salt_bytes = secrets.token_bytes(16)
        new_password = new_password.encode("utf-8")
        new_hash = hashlib.pbkdf2_hmac(
            "sha256", new_password, salt_bytes, PASSWORD_ITERATIONS
        )
        self._salt = salt_bytes.hex()
        self._hashed_password = new_hash.hex()


class Wallet:
    """Кошелёк пользователя для одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        if type(currency_code) is not str:
            raise TypeError("Код валюты должен быть строковым значением")
        if not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")
        self.currency_code = currency_code.strip().upper()
        self.balance = balance

    @property
    def balance(self):
        """Геттер: возвращает баланс пользователя"""
        return self._balance

    @balance.setter
    def balance(self, amount):
        """Сеттер: проверяет баланс пользователя"""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if not math.isfinite(amount):
            raise ValueError("Баланс должен быть конечным числом")
        if amount < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(amount)

    def deposit(self, amount: float):
        """Пополняет баланс"""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Депозит должен быть числом")
        if not math.isfinite(amount):
            raise ValueError("Депозит должен быть конечным числом")
        if amount <= 0:
            raise ValueError("Депозит должен быть больше 0")
        self.balance += amount

    def get_balance_info(self):
        """Предоставляет информецию о балансе"""
        return {"currency_code": self.currency_code, "balance": self.balance}

    def withdraw(self, amount: float):
        """Выводит средства с баланса"""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма вывода должена быть числом")
        if not math.isfinite(amount):
            raise ValueError("Сумма вывода должена быть конечным числом")
        if amount <= 0:
            raise ValueError("Сумма вывода не может быть отрицательным")
        if self.balance < amount:
            raise InsufficientFundsError(self.balance, amount, self.currency_code)
        self.balance -= amount


class Portfolio:
    """Управляет валютными кошельками пользователя."""

    def __init__(self, user: User):
        if not isinstance(user, User):
            raise TypeError("Ожидается объект класса User")
        self._user = user
        self._user_id = user.user_id
        self._wallets = {}

    @property
    def user(self):
        """Возвращает объект пользователя."""
        return self._user

    @property
    def wallets(self):
        """Геттер: возвращает копию словаря кошельков"""
        return self._wallets.copy()

    def add_currency(self, currency_code):
        """Добавляет новый кошелек в портфель"""
        wallet = Wallet(currency_code)
        if wallet.currency_code in self._wallets:
            raise ValueError("Такой кошелек уже существует")
        self._wallets[wallet.currency_code] = wallet

    def get_wallet(self, currency_code):
        """Возвращает объект Wallet по коду валюты"""
        if not isinstance(currency_code, str):
            raise TypeError("Код валюты должен быть строкой")
        currency_code = currency_code.strip().upper()
        if not currency_code:
            raise ValueError("Код валюты не может быть пустым")
        try:
            return self._wallets[currency_code]
        except KeyError as error:
            raise KeyError(f"Кошелек {currency_code} не найден") from error

    def get_total_value(self, exchange_rates, base_currency="USD"):
        """Возвращает общую стоимость портфеля в базовой валюте"""
        if not isinstance(base_currency, str):
            raise TypeError("Код валюты должен быть строкой")
        base_currency = base_currency.strip().upper()
        if not base_currency:
            raise ValueError("Код валюты не может быть пустым")
        if not isinstance(exchange_rates, dict):
            raise TypeError("Курсы валют болжны быть словарем")
        if base_currency not in exchange_rates:
            raise ValueError("Базового курса нет в курсах валют")
        full_balans = 0.0
        for v in exchange_rates.values():
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError("Курс должен быть числом")
            if not math.isfinite(v):
                raise ValueError("Курс должен быть конечным числом")
            if v <= 0:
                raise ValueError("Курс должен быть больше 0")
        for k, v in self._wallets.items():
            if v.balance == 0:
                continue
            try:
                full_balans += exchange_rates[k] * v.balance
            except KeyError as error:
                raise KeyError(f"Курс {k} не найден") from error
        return full_balans / exchange_rates[base_currency]
