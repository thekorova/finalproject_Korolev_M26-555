from valutatrade_hub.core.utils import load_json, save_json


class DatabaseManager:
    """Управляет загрузкой и сохранением данных"""

    _instance = None

    # выбран __new__ из-за простоты, да и читается лучше
    # лучше воспринимается чтоли и понятнее в использовании
    # но по сути метакласс лучше когда много классов
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, path, default):
        """Загружает данные из json"""
        return load_json(path, default)

    def save(self, path, data):
        """Сохраняет данные в JSON-файл."""
        return save_json(path, data)
