# Импортируем типы колонок из SQLAlchemy:
# - Column: базовый класс для определения колонок таблицы
# - Integer: целочисленный тип данных
# - String: строковый тип (VARCHAR в PostgreSQL)
# - JSON: тип для хранения JSON-данных (в PostgreSQL - JSONB)
# - DateTime: тип для хранения даты и времени
# - ForeignKey: для создания внешнего ключа (связи между таблицами)
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey

# Импортируем declarative_base - функцию, которая создаёт базовый класс
# для декларативного определения моделей ORM
# Все модели должны наследоваться от этого базового класса
from sqlalchemy.ext.declarative import declarative_base

# Импортируем relationship - для определения связей между моделями
# Позволяет удобно навигировать между связанными объектами
from sqlalchemy.orm import relationship

# Импортируем datetime для работы с датой и временем
# datetime.utcnow - функция для получения текущего UTC времени
from datetime import datetime

# Создаём базовый класс для всех моделей
# declarative_base() возвращает класс, который будет использоваться
# как основа для определения таблиц в декларативном стиле
Base = declarative_base()


# Определяем модель PlantModel (Модель технологической установки)
# Наследуемся от Base, чтобы SQLAlchemy мог автоматически создать таблицу
class PlantModel(Base):
    """
    Модель для хранения структуры технологической установки:
    - потоки (flows)
    - узлы (nodes)
    - ограничения (constraints)
    Эта модель является "шаблоном" для балансировки.
    """

    # Указываем имя таблицы в базе данных
    # Будет создана таблица с именем "plant_models"
    __tablename__ = "plant_models"

    # Поле id - первичный ключ (primary_key)
    # index=True - создаёт индекс для быстрого поиска по этому полю
    # Integer - целочисленный тип (автоинкремент в PostgreSQL)
    id = Column(Integer, primary_key=True, index=True)

    # Поле name - название модели установки
    # String - строковый тип (без указания длины - TEXT в PostgreSQL)
    # nullable=False - поле обязательное, не может быть NULL
    name = Column(String, nullable=False)

    # Поле description - описание модели
    # nullable=True - поле необязательное, может быть NULL
    description = Column(String, nullable=True)

    # Поле version - версия модели (для отслеживания изменений)
    # default=1 - значение по умолчанию, если не указано иное
    version = Column(Integer, default=1)

    # Поле created_at - дата и время создания записи
    # default=datetime.utcnow - при создании записи автоматически
    # подставляется текущее UTC время (функция, а не её результат!)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Поле flows - хранит данные о потоках в формате JSON
    # nullable=False - обязательно должно быть заполнено
    # Содержит список словарей: [{"id": "F1", "name": "Поток 1", ...}, ...]
    flows = Column(JSON, nullable=False)

    # Поле nodes - хранит данные об узлах в формате JSON
    # nullable=False - обязательно должно быть заполнено
    # Содержит список словарей: [{"id": "N1", "name": "Узел 1", "equations": [...]}, ...]
    nodes = Column(JSON, nullable=False)

    # Поле constraints - хранит дополнительные ограничения в формате JSON
    # default=list - по умолчанию пустой список
    # Может содержать ограничения вида: [{"terms": [...], "rhs": 0}, ...]
    constraints = Column(JSON, default=list)

    # Определяем связь "один ко многим" с моделью MeasurementData
    # measurements - имя атрибута, через который будем получать измерения
    # relationship - создаёт виртуальную связь (не хранится в БД)
    # back_populates="plant_model" - обратная связь в модели MeasurementData
    # Это позволяет писать: plant_model.measurements (все измерения для модели)
    measurements = relationship("MeasurementData", back_populates="plant_model")


# Определяем модель MeasurementData (Данные измерений)
class MeasurementData(Base):
    """
    Модель для хранения измеренных значений потоков
    для конкретной модели установки за определённый период времени.
    """

    # Имя таблицы в базе данных
    __tablename__ = "measurement_data"

    # Первичный ключ (автоинкрементный ID)
    id = Column(Integer, primary_key=True, index=True)

    # Внешний ключ (Foreign Key) - ссылается на таблицу plant_models
    # ForeignKey("plant_models.id") - указывает, что это поле связано
    # с полем id таблицы plant_models
    # Это обеспечивает ссылочную целостность на уровне БД
    plant_model_id = Column(Integer, ForeignKey("plant_models.id"))

    # Название периода (например, "2024-01-15", "январь_2024", "смена_А")
    # nullable=False - обязательно должно быть указано
    period_name = Column(String, nullable=False)

    # Описание периода (например, "Данные за январь 2024 года")
    # nullable=True - необязательное поле
    description = Column(String, nullable=True)

    # Временная метка создания записи
    # default=datetime.utcnow - автоматическая установка текущего времени
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Поле measurements - хранит измерения в формате JSON
    # nullable=False - обязательно должно быть заполнено
    # Содержит список словарей: [{"flow_id": "F1", "value": 100.5}, ...]
    measurements = Column(JSON, nullable=False)

    # Определяем обратную связь к модели PlantModel
    # plant_model - имя атрибута для доступа к связанной модели установки
    # back_populates="measurements" - соответствует атрибуту в PlantModel
    # Это позволяет писать: measurement.plant_model (получить модель установки)
    plant_model = relationship("PlantModel", back_populates="measurements")