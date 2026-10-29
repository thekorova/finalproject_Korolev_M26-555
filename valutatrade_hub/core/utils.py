import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_json(filepath, default):
    """Загружает данные из json"""
    try:
        with open(filepath, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return default


def save_json(filepath, data):
    """Атомарно сохраняет данные в JSON."""
    filepath = Path(filepath)
    temp_path = filepath.with_suffix(".json.tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False)
        os.replace(temp_path, filepath)
    finally:
        temp_path.unlink(missing_ok=True)
