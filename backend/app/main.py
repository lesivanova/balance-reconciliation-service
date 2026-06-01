# Импортируем классы FastAPI и HTTPException из модуля fastapi
# FastAPI - основной класс для создания веб-приложения
# HTTPException - класс для возврата HTTP-ошибок с нужным статус-кодом
from fastapi import FastAPI, HTTPException

# Импортируем middleware для поддержки CORS (Cross-Origin Resource Sharing)
# CORS нужен, чтобы разрешить фронтенду с другого домена обращаться к нашему API
from fastapi.middleware.cors import CORSMiddleware

# Импортируем Pydantic-схемы (модели данных) из локального модуля schemas
# BalanceRequest - схема входящего запроса (что ожидаем от клиента)
# BalanceResponse - схема ответа сервера (что вернём клиенту)
# BalancedFlow - схема сбалансированного потока (входит в ответ)
from .schemas import BalanceRequest, BalanceResponse, BalancedFlow

# Импортируем класс решателя задачи балансировки из модуля qp_solver
# Этот класс содержит логику оптимизации (возможно, квадратичное программирование)
from .qp_solver import BalanceSolver

# Создаём экземпляр приложения FastAPI
# title - заголовок API, который будет виден в автоматической документации (Swagger/ReDoc)
# version - версия сервиса
app = FastAPI(title="Balance Reconciliation Service", version="1.0.0")

# Добавляем middleware для обработки CORS
# allow_origins=["*"] - разрешаем запросы с любых источников (для разработки/тестирования,
#                      в продакшене лучше указать конкретные домены)
# allow_credentials=True - разрешаем передавать куки и заголовки авторизации
# allow_methods=["*"] - разрешаем все HTTP-методы (GET, POST, PUT, DELETE и т.д.)
# allow_headers=["*"] - разрешаем все заголовки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаём единственный экземпляр решателя (синглтон в рамках приложения)
# Это эффективно, так как не нужно создавать объект при каждом запросе
solver = BalanceSolver()


# Определяем endpoint для проверки работоспособности сервиса (health check)
# @app.get - означает, что обработчик отвечает на HTTP GET запросы
# "/health" - URL, по которому доступен endpoint
# async def - асинхронная функция (позволяет FastAPI эффективно обрабатывать I/O)
@app.get("/health")
async def health_check():
    # Возвращаем JSON-объект с полями status и version
    return {"status": "healthy", "version": "1.0.0"}


# POST-эндпоинт для балансировки данных (основная логика)
# "/api/v1/reconcile" - URL с версионированием API (v1)
# response_model=BalanceResponse - схема, которой должен соответствовать ответ
@app.post("/api/v1/reconcile", response_model=BalanceResponse)
async def reconcile_balance(request: BalanceRequest):
    # Извлекаем множество id всех потоков из запроса
    # Генератор множества: {f.id for f in request.flows}
    # Множество используется для быстрой проверки принадлежности (O(1))
    flow_ids = {f.id for f in request.flows}

    # Валидация: проверяем, что все flow_id, упомянутые в уравнениях узлов, существуют
    for node in request.nodes:  # перебираем все узлы
        for eq in node.equations:  # перебираем все уравнения в узле
            if eq.flow_id not in flow_ids:  # если flow_id нет среди существующих потоков
                # Возвращаем HTTP ошибку 400 (Bad Request) с пояснением
                raise HTTPException(status_code=400, detail=f"Поток {eq.flow_id} не найден")

    # Преобразуем Pydantic-объекты в словари для передачи в решатель
    # .dict() - метод Pydantic, превращающий модель в Python dict
    flows = [f.dict() for f in request.flows]
    nodes = [n.dict() for n in request.nodes]

    # Обрабатываем ограничения (constraints), если они есть
    # Если constraints не переданы (None), то оставляем None
    constraints = [c.dict() for c in request.constraints] if request.constraints else None

    # Вызываем метод solve решателя, передавая словари с данными
    result = solver.solve(flows, nodes, constraints)

    # Если статус решения не "success" (например, "error" или "infeasible")
    if result['status'] != 'success':
        # Возвращаем ошибку 400 с сообщением из решателя или стандартным текстом
        raise HTTPException(status_code=400, detail=result.get('message', 'Ошибка решения'))

    # Формируем успешный ответ
    # BalanceResponse - Pydantic-модель, которая автоматически валидирует и сериализует данные
    return BalanceResponse(
        status=result['status'],  # статус ("success")
        balanced_flows=[BalancedFlow(**f) for f in result['balanced_flows']],  # преобразуем словари в модели
        max_disbalance=result['max_disbalance'],  # максимальная невязка после балансировки
        iterations=result['iterations'],  # количество итераций оптимизатора
        global_test=result.get('global_test'),  # результат глобального теста (если есть)
        global_test_limit=result.get('global_test_limit'),  # порог для глобального теста
        global_test_original=result.get('global_test_original'),  # исходное значение до балансировки
        is_consistent=result.get('is_consistent'),  # согласована ли система уравнений
        degrees_of_freedom=result.get('degrees_of_freedom')  # степени свободы системы
    )


# POST-эндпоинт для обнаружения грубых ошибок (выбросов) в данных
# response_model=None - означает, что ответ не будет автоматически валидироваться (может быть любым dict)
@app.post("/api/v1/detect-errors", response_model=None)
async def detect_gross_errors(request: BalanceRequest):
    # Подготавливаем данные аналогично предыдущему эндпоинту
    flows = [f.dict() for f in request.flows]
    nodes = [n.dict() for n in request.nodes]
    constraints = [c.dict() for c in request.constraints] if request.constraints else None

    # Вызываем метод detect_gross_errors у решателя
    result = solver.detect_gross_errors(flows, nodes, constraints)

    # Возвращаем результат напрямую (без обёртки в Pydantic-модель)
    return result