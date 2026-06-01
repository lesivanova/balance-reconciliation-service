# Импортируем основные компоненты FastAPI:
# - FastAPI: класс для создания веб-приложения
# - Depends: используется для внедрения зависимостей (например, сессии БД)
# - HTTPException: для возврата HTTP-ошибок с нужным статус-кодом
from fastapi import FastAPI, Depends, HTTPException

# Импортируем Session из SQLAlchemy ORM для аннотации типа сессии
# Session используется как тип для параметра db в эндпоинтах
from sqlalchemy.orm import Session

# Импортируем List из typing для аннотации списков в response_model
from typing import List

# Импортируем httpx - асинхронный HTTP клиент для вызовов внешних сервисов
# Используется для отправки запросов к сервису балансировки (solver)
import httpx

# Импортируем модуль os для работы с переменными окружения
import os

# Абсолютные импорты из модулей нашего приложения
# database: содержит get_db (dependency) и init_db (инициализация БД)
from database import get_db, init_db

# models: содержит SQLAlchemy модели PlantModel и MeasurementData
from models import PlantModel, MeasurementData

# schemas: содержит Pydantic-схемы для валидации данных
from schemas import (
    PlantModelCreate,  # Схема для создания модели установки
    PlantModelResponse,  # Схема ответа с данными модели
    MeasurementDataCreate,  # Схема для создания измерений
    MeasurementDataResponse,  # Схема ответа с измерениями
    ReconcileRequest  # Схема запроса на балансировку
)

# Создаём экземпляр FastAPI приложения
# title - название сервиса, отображаемое в документации Swagger
# version - версия API
app = FastAPI(title="Database Service", version="1.0.0")

# Определяем URL сервиса балансировки (solver) из переменной окружения
# SOLVER_URL - можно задать при запуске, например: export SOLVER_URL=http://localhost:8000
# По умолчанию используется "http://backend-service:8000" (для Docker-сети)
SOLVER_URL = os.environ.get("SOLVER_URL", "http://backend-service:8000")


# Декоратор @app.on_event("startup") - функция выполняется при запуске приложения
# Это событие происходит один раз перед началом обработки запросов
@app.on_event("startup")
def startup():
    """
    Инициализация базы данных при старте приложения.
    Создаёт все необходимые таблицы, если они ещё не существуют.
    """
    # Вызываем init_db() из database.py для создания таблиц
    init_db()


# Эндпоинт для проверки работоспособности сервиса
# @app.get - обрабатывает HTTP GET запросы
# "/health" - URL эндпоинта (обычно используется для health checks)
@app.get("/health")
def health():
    """Простая проверка, что сервис работает"""
    return {"status": "healthy"}  # Возвращаем JSON с полем status


# POST-эндпоинт для создания новой модели технологической установки
# response_model=PlantModelResponse - автоматическая валидация и сериализация ответа
@app.post("/api/plant-models", response_model=PlantModelResponse)
def create_plant_model(
        model: PlantModelCreate,  # Pydantic-модель из тела запроса
        db: Session = Depends(get_db)  # Внедрение сессии БД (зависимость)
):
    """
    Создаёт новую модель установки (структуру потоков и узлов).
    Сохраняет её в базу данных и возвращает созданную модель с ID.
    """

    # Преобразуем Pydantic-объекты в словари для хранения в JSON-полях
    # model.flows - список объектов FlowInput
    # .dict() - метод Pydantic для преобразования в словарь
    flows = [f.dict() for f in model.flows]
    nodes = [n.dict() for n in model.nodes]

    # Создаём экземпляр SQLAlchemy модели PlantModel
    db_model = PlantModel(
        name=model.name,  # Название модели
        description=model.description,  # Описание
        flows=flows,  # Список потоков (хранится как JSON)
        nodes=nodes,  # Список узлов (хранится как JSON)
        constraints=model.constraints or []  # Ограничения (если есть, иначе пустой список)
    )

    # Добавляем объект в сессию (помечаем для вставки в БД)
    db.add(db_model)

    # Фиксируем транзакцию - сохраняем изменения в базе данных
    db.commit()

    # Обновляем объект из БД (получаем сгенерированные поля, например id)
    db.refresh(db_model)

    # Возвращаем модель (автоматически преобразуется в PlantModelResponse)
    return db_model


# GET-эндпоинт для получения списка всех моделей установок
# response_model=List[PlantModelResponse] - возвращаем список моделей
@app.get("/api/plant-models", response_model=List[PlantModelResponse])
def get_plant_models(db: Session = Depends(get_db)):
    """
    Возвращает список всех сохранённых моделей установок.
    """
    # db.query(PlantModel) - создаём запрос к таблице PlantModel
    # .all() - выполняем запрос и возвращаем все строки
    return db.query(PlantModel).all()


# GET-эндпоинт для получения конкретной модели по ID
# {model_id} - параметр пути (path parameter)
@app.get("/api/plant-models/{model_id}", response_model=PlantModelResponse)
def get_plant_model(
        model_id: int,  # ID модели из URL
        db: Session = Depends(get_db)  # Сессия БД
):
    """
    Возвращает модель установки по её ID.
    Если модель не найдена - возвращает ошибку 404.
    """

    # Выполняем запрос: фильтруем по ID и берём первую запись
    model = db.query(PlantModel).filter(PlantModel.id == model_id).first()

    # Если модель не найдена (None)
    if not model:
        # Поднимаем HTTP исключение с кодом 404 (Not Found)
        raise HTTPException(status_code=404, detail="Модель не найдена")

    # Возвращаем найденную модель
    return model


# POST-эндпоинт для сохранения измерений для конкретной модели
# {model_id} - ID модели, к которой относятся измерения
@app.post("/api/measurements/{model_id}", response_model=MeasurementDataResponse)
def create_measurement(
        model_id: int,  # ID модели из URL
        measurement: MeasurementDataCreate,  # Данные измерений из тела запроса
        db: Session = Depends(get_db)  # Сессия БД
):
    """
    Сохраняет измерения (значения потоков) для указанной модели и периода.
    """

    # Проверяем, существует ли модель с таким ID
    model = db.query(PlantModel).filter(PlantModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Модель не найдена")

    # Создаём запись измерений в БД
    db_measurement = MeasurementData(
        plant_model_id=model_id,  # Внешний ключ на модель
        period_name=measurement.period_name,  # Название периода (например, "2024-01")
        description=measurement.description,  # Описание периода
        measurements=measurement.measurements  # Список измерений (хранится как JSON)
    )

    # Добавляем в сессию
    db.add(db_measurement)

    # Сохраняем в БД
    db.commit()

    # Обновляем объект (получаем id и timestamp)
    db.refresh(db_measurement)

    return db_measurement


# GET-эндпоинт для получения всех измерений для модели
@app.get("/api/measurements/{model_id}", response_model=List[MeasurementDataResponse])
def get_measurements(
        model_id: int,  # ID модели
        db: Session = Depends(get_db)  # Сессия БД
):
    """
    Возвращает список всех измерений (по всем периодам) для указанной модели.
    """

    # Запрос: фильтр по plant_model_id, сортировка по умолчанию - по id
    return db.query(MeasurementData).filter(
        MeasurementData.plant_model_id == model_id
    ).all()


# GET-эндпоинт для получения измерений за конкретный период
@app.get("/api/measurements/{model_id}/{period_name}", response_model=MeasurementDataResponse)
def get_measurement_by_period(
        model_id: int,  # ID модели
        period_name: str,  # Название периода из URL
        db: Session = Depends(get_db)  # Сессия БД
):
    """
    Возвращает измерения для конкретной модели и конкретного периода.
    """

    # Запрос с двумя условиями фильтрации
    measurement = db.query(MeasurementData).filter(
        MeasurementData.plant_model_id == model_id,  # Условие 1: ID модели
        MeasurementData.period_name == period_name  # Условие 2: название периода
    ).first()  # Берём первую (и единственную) запись

    # Если данные не найдены
    if not measurement:
        raise HTTPException(status_code=404, detail="Данные не найдены")

    return measurement


# GET-эндпоинт для получения визуализации модели (структуры)
# response_model не указан - значит возвращаем произвольный JSON
@app.get("/api/plant-models/{model_id}/visualization")
def get_model_visualization(
        model_id: int,  # ID модели
        db: Session = Depends(get_db)  # Сессия БД
):
    """
    Возвращает данные модели в формате, удобном для визуализации.
    Используется фронтендом для отображения графа потоков.
    """

    # Ищем модель по ID
    model = db.query(PlantModel).filter(PlantModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Модель не найдена")

    # Возвращаем обогащённый объект со статистикой
    return {
        "id": model.id,  # ID модели
        "name": model.name,  # Название
        "flows": model.flows,  # Список потоков
        "nodes": model.nodes,  # Список узлов
        "stats": {  # Статистика модели
            "flow_count": len(model.flows),  # Количество потоков
            "node_count": len(model.nodes)  # Количество узлов
        }
    }


# POST-эндпоинт для выполнения балансировки с использованием сохранённых данных
@app.post("/api/reconcile")
async def reconcile_with_saved_data(
        request: ReconcileRequest,  # Запрос: plant_model_id + period_name
        db: Session = Depends(get_db)  # Сессия БД
):
    """
    Выполняет балансировку для сохранённой модели и измерений.
    Загружает модель и измерения из БД, формирует запрос к solver-сервису.
    """

    # 1. Загружаем модель установки из БД
    model = db.query(PlantModel).filter(PlantModel.id == request.plant_model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Модель не найдена")

    # 2. Загружаем измерения за указанный период
    measurement = db.query(MeasurementData).filter(
        MeasurementData.plant_model_id == request.plant_model_id,
        MeasurementData.period_name == request.period_name
    ).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Данные за период не найдены")

    # 3. Создаём словарь для быстрого поиска значений измерений по flow_id
    #    measurements = [{"flow_id": "F1", "value": 100}, ...]
    #    Превращаем в {"F1": 100, "F2": 200, ...}
    measurements_dict = {m["flow_id"]: m["value"] for m in measurement.measurements}

    # 4. Обогащаем потоки измеренными значениями
    flows_with_data = []
    for flow in model.flows:
        # Копируем словарь потока (чтобы не изменять оригинал)
        flow_copy = flow.copy()

        # Если для этого потока есть измерение в сохранённых данных
        if flow["id"] in measurements_dict:
            # Подставляем измеренное значение
            flow_copy["measured_value"] = measurements_dict[flow["id"]]
        # Если измерения нет, оставляем значение по умолчанию (из модели)

        # Добавляем в список
        flows_with_data.append(flow_copy)

    # 5. Отправляем асинхронный HTTP-запрос к сервису балансировки
    #    async with - контекстный менеджер для управления сессией httpx
    async with httpx.AsyncClient() as client:
        # POST-запрос к эндпоинту solver-сервиса
        response = await client.post(
            f"{SOLVER_URL}/api/v1/reconcile",  # URL solver-сервиса
            json={  # Тело запроса в формате JSON
                "flows": flows_with_data,  # Потоки с измерениями
                "nodes": model.nodes,  # Узлы (структура)
                "constraints": model.constraints  # Ограничения
            },
            timeout=30.0  # Таймаут 30 секунд
        )

        # 6. Обрабатываем ответ от solver-сервиса
        if response.status_code != 200:
            # Если произошла ошибка - пробрасываем её клиенту
            raise HTTPException(status_code=response.status_code, detail=response.text)

        # 7. Возвращаем результат балансировки клиенту
        return response.json()