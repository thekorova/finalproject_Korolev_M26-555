import tomllib


class SettingsLoader:
    """Загружает и хранит настройки приложения."""

    _instance = None

    # выбран __new__ из-за простоты, да и читается лучше
    # лучше воспринимается чтоли и понятнее в использовании
    # но по сути метакласс лучше когда много классов
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_settings"):
            return
        with open("pyproject.toml", "rb") as file:
            config = tomllib.load(file)
        self._settings = config["tool"]["valutatrade"]

    def get(self, key: str, default=None):
        """Возвращает значение настроек"""
        return self._settings.get(key, default)
