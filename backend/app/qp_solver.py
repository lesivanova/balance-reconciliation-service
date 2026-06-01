# ============================================================================
# ИМПОРТ БИБЛИОТЕК
# ============================================================================

# Импортируем NumPy - библиотека для эффективных матричных вычислений
# Используется для векторных операций, матриц, линейной алгебры
import numpy as np

# Импортируем из scipy.optimize:
# - minimize - функция для численной оптимизации (поиска минимума целевой функции)
# - Bounds - класс для задания граничных условий на переменные
from scipy.optimize import minimize, Bounds

# Импортируем scipy.stats - модуль для статистических распределений
# Используется для хи-квадрат распределения при глобальном тесте
from scipy import stats

# Импортируем pinv из scipy.linalg - псевдообратная матрица Мура-Пенроуза
# Используется для решения плохо обусловленных систем в глобальном тесте
from scipy.linalg import pinv

# Импортируем типы данных из модуля typing для аннотаций
# List - список, Dict - словарь, Optional - опциональное значение (может быть None)
from typing import List, Dict, Optional


# ============================================================================
# ФУНКЦИЯ КОНВЕРТАЦИИ NUMPY ТИПОВ В PYTHON ТИПЫ
# ============================================================================

def to_python(obj):
    """
    Конвертирует numpy типы в стандартные Python типы
    Нужно, потому что FastAPI не умеет сериализовать numpy типы в JSON
    """
    # Проверяем, является ли объект булевым типом NumPy или стандартным bool
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)  # np.bool_ → bool (True/False)

    # Проверяем, является ли объект целочисленным типом NumPy или стандартным int
    elif isinstance(obj, (np.integer, int)):
        return int(obj)  # np.int64 → int (1, 2, 3...)

    # Проверяем, является ли объект вещественным типом NumPy или стандартным float
    elif isinstance(obj, (np.floating, float)):
        return float(obj)  # np.float64 → float (1.5, 2.3...)

    # Проверяем, является ли объект массивом NumPy
    elif isinstance(obj, np.ndarray):
        return obj.tolist()  # np.ndarray → list ([1, 2, 3])

    # Проверяем, является ли объект словарём
    elif isinstance(obj, dict):
        # Рекурсивно применяем to_python к каждому значению в словаре
        return {k: to_python(v) for k, v in obj.items()}

    # Проверяем, является ли объект списком или кортежем
    elif isinstance(obj, (list, tuple)):
        # Рекурсивно применяем to_python к каждому элементу
        return [to_python(i) for i in obj]

    # Если объект уже стандартного типа Python, возвращаем его без изменений
    return obj


# ============================================================================
# КЛАСС BALANCE_SOLVER - ОСНОВНОЙ КЛАСС ДЛЯ РАСЧЁТА БАЛАНСА
# ============================================================================

class BalanceSolver:
    """Класс для решения задачи балансировки потоков данных"""

    # ------------------------------------------------------------------------
    # ОСНОВНОЙ МЕТОД РЕШЕНИЯ ЗАДАЧИ БАЛАНСИРОВКИ
    # ------------------------------------------------------------------------

    def solve(self, flows: List[Dict], nodes: List[Dict], constraints: Optional[List[Dict]] = None):
        """
        Основной метод балансировки потоков

        Параметры:
        - flows: список словарей с данными о потоках (id, measured_value, tolerance...)
        - nodes: список словарей с узлами и уравнениями баланса
        - constraints: опциональные дополнительные линейные ограничения

        Возвращает:
        - словарь со статусом, сбалансированными потоками, глобальным тестом
        """

        # Определяем количество потоков (переменных оптимизации)
        n = len(flows)

        # Извлекаем ID всех потоков в отдельный список
        flow_ids = [f['id'] for f in flows]

        # Начальное приближение - измеренные значения потоков
        # Преобразуем в массив NumPy для векторных операций
        x0 = np.array([f['measured_value'] for f in flows])

        # Массив допусков (погрешностей) измерений для каждого потока
        tols = np.array([f['tolerance'] for f in flows])

        # Нижние границы для переменных (минимально допустимые значения)
        # Если min_value не указан, используем 0
        lb = np.array([f.get('min_value', 0) for f in flows])

        # Верхние границы для переменных (максимально допустимые значения)
        # Если max_value не указан, используем 10000
        ub = np.array([f.get('max_value', 10000) for f in flows])

        # Строим матрицу ограничений-равенств Aeq (балансовые уравнения для узлов)
        # Возвращает матрицу размером (количество_узлов × количество_потоков)
        Aeq = self._build_matrix(nodes, flow_ids, n)

        # Правая часть уравнений баланса (для каждого узла сумма потоков = 0)
        beq = np.zeros(len(nodes))  # Все нули, так как Σ(потоки) = 0

        # Инициализируем массив обратных допусков нулями
        inv_tols = np.zeros(n)

        # Вычисляем обратные допуски (1/tolerance) для нормировки
        # Чем меньше допуск, тем больше вес (больше доверия измерению)
        for i, tol in enumerate(tols):
            if tol > 0:  # Исключаем деление на ноль
                inv_tols[i] = 1.0 / tol

        # Формируем матрицу Гессе (H) для квадратичной целевой функции
        # H = диагональная матрица из квадратов обратных допусков
        # Это взвешивает отклонения: потоки с малым допуском имеют больший вес
        H = np.diag(inv_tols ** 2)

        # Формируем линейный член целевой функции: f = -H * x0
        # Целевая функция имеет вид: 0.5 * x^T * H * x + f^T * x
        # При таком f минимум достигается при x близком к x0 с учётом весов H
        f = -H @ x0  # @ - оператор матричного умножения в Python 3.5+

        # Если переданы дополнительные ограничения (constraints)
        if constraints:
            # Строим матрицу дополнительных ограничений и правую часть
            A_extra, b_extra = self._build_constraints(constraints, flow_ids, n)

            # Если ограничения есть (A_extra не None)
            if A_extra is not None:
                # Добавляем дополнительные строки к матрице Aeq (вертикальное объединение)
                Aeq = np.vstack([Aeq, A_extra])
                # Добавляем соответствующие значения к правой части beq
                beq = np.hstack([beq, b_extra])

        # Пытаемся решить оптимизационную задачу
        try:
            # Определяем ограничения-равенства для передаче в minimize
            # cons: словарь с типом 'eq' (equality) и функцией невязки
            # Невязка должна быть равна 0: Aeq @ x - beq = 0
            cons = {'type': 'eq', 'fun': lambda x: Aeq @ x - beq}

            # Создаём объект границ для переменных (нижние и верхние)
            bounds = Bounds(lb, ub)

            # Определяем целевую функцию квадратичного программирования
            def objective(x):
                # Вычисляем значение: 0.5 * x^T * H * x + f^T * x
                # @ - матричное умножение для векторов
                return 0.5 * x @ H @ x + f @ x

            # Вызываем оптимизатор minimize
            # method='SLSQP' - Sequential Least Squares Quadratic Programming
            #   Подходит для задач с ограничениями-равенствами и границами
            # x0 - начальное приближение
            # constraints - ограничения-равенства
            # bounds - границы переменных
            # options - настройки: maxiter (макс. итераций), disp (вывод отладочной инфо)
            result = minimize(objective, x0, method='SLSQP',
                              constraints=cons, bounds=bounds,
                              options={'maxiter': 500, 'disp': False})

            # Если оптимизация успешна (result.success == True)
            if result.success:
                # Список для хранения сбалансированных потоков
                balanced_flows = []

                # Перебираем все потоки с индексами
                for i, flow in enumerate(flows):
                    # Добавляем словарь с результатами для каждого потока
                    balanced_flows.append({
                        'id': flow['id'],  # ID потока
                        'name': flow['name'],  # Название потока
                        'original_value': float(x0[i]),  # Исходное измеренное значение
                        'balanced_value': float(result.x[i]),  # Сбалансированное значение (решение)
                        'correction': float(result.x[i] - x0[i]),  # Поправка (на сколько изменили)
                        # Относительная погрешность в процентах (если исходное не ноль)
                        'relative_error': abs(result.x[i] - x0[i]) / x0[i] * 100 if x0[i] != 0 else 0
                    })

                # Вычисляем глобальный статистический тест (критерий согласия)
                gt_result = self._calc_global_test(Aeq, x0, tols)

                # Возвращаем результат, преобразуя все NumPy типы в стандартные Python
                return to_python({
                    'status': 'success',  # Статус решения
                    'balanced_flows': balanced_flows,  # Список сбалансированных потоков
                    'max_disbalance': 0.0,  # Максимальная невязка (всегда 0 для равенств)
                    'iterations': result.nit,  # Количество итераций оптимизатора
                    'global_test': gt_result['GTst'],  # Нормированный глобальный тест
                    'global_test_limit': gt_result['GT_limit'],  # Критическое значение хи-квадрат
                    'global_test_original': gt_result['GT_original'],  # Исходное значение теста
                    'is_consistent': gt_result['is_consistent'],  # Согласована ли система
                    'degrees_of_freedom': gt_result['degrees_of_freedom'],  # Степени свободы
                })
            else:
                # Если оптимизатор не нашёл решение
                return {'status': 'failed', 'message': 'Решение не найдено'}

        except Exception as e:
            # В случае любой ошибки (например, плохо обусловленная матрица)
            return {'status': 'error', 'message': str(e)}

    # ------------------------------------------------------------------------
    # ВЫЧИСЛЕНИЕ ГЛОБАЛЬНОГО СТАТИСТИЧЕСКОГО ТЕСТА
    # ------------------------------------------------------------------------

    def _calc_global_test(self, Aeq, x0, tolerances):
        """
        Вычисление глобального статистического теста для проверки согласованности данных

        Параметры:
        - Aeq: матрица ограничений (балансовые уравнения)
        - x0: измеренные значения потоков
        - tolerances: допуски измерений

        Возвращает: нормированный тест, исходное значение, критическое значение,
                   степени свободы, флаг согласованности
        """

        # Количество переменных (потоков)
        n = len(x0)

        # Количество ограничений (узлов + дополнительные)
        m = Aeq.shape[0]  # shape[0] - число строк матрицы

        # Коэффициент для пересчёта допуска в среднеквадратичное отклонение
        # 1.96 соответствует квантили 97.5% стандартного нормального распределения
        # Это предполагает, что допуск = 1.96 * sigma (95% доверительный интервал)
        coef_delta = 1.96

        # Пересчитываем допуски в среднеквадратичные отклонения (sigma)
        xStd = np.array(tolerances) / coef_delta

        # Строим ковариационную матрицу погрешностей измерений
        # Предполагаем, что погрешности независимы, поэтому матрица диагональная
        xSigma = np.diag(xStd ** 2)

        # Вектор невязок ограничений (насколько измеренные значения нарушают баланс)
        # r = Aeq * x0 (должен быть 0 в идеале)
        r = Aeq @ x0

        # Ковариационная матрица невязок: V = Aeq * Σ_x * Aeq^T
        # По закону распространения погрешностей
        V = Aeq @ xSigma @ Aeq.T

        # Вычисляем исходное значение глобального теста (статистика хи-квадрат)
        try:
            # GT = r^T * pseudoinverse(V) * r
            # Используем псевдообратную матрицу для устойчивости при плохой обусловленности
            GT_original = float(r.T @ pinv(V) @ r)
        except:
            # В случае ошибки (например, сингулярная матрица) возвращаем 0
            GT_original = 0.0

        # Уровень значимости для теста (5%)
        alpha = 0.05

        # Степени свободы = количество ограничений
        degrees_of_freedom = m

        # Критическое значение хи-квадрат распределения
        # ppf - percent point function (обратная функция распределения)
        GT_limit = float(stats.chi2.ppf(1 - alpha, degrees_of_freedom))

        # Нормированное значение теста (для удобства интерпретации)
        # Если GTst > 1, данные статистически не согласованы
        if GT_original == 0 and GT_limit == 0:
            GTst = 0.0  # Защита от деления на ноль
        else:
            GTst = GT_original / GT_limit

        # Проверяем, согласованы ли данные на уровне значимости 5%
        # is_consistent = True, если GT_original <= GT_limit (данные не противоречат модели)
        is_consistent = GT_original <= GT_limit

        # Возвращаем все вычисленные значения в словаре
        return {
            'GTst': GTst,  # Нормированный тест
            'GT_original': GT_original,  # Исходное значение
            'GT_limit': GT_limit,  # Критическое значение
            'degrees_of_freedom': degrees_of_freedom,  # Степени свободы
            'is_consistent': is_consistent,  # Флаг согласованности
        }

    # ------------------------------------------------------------------------
    # ВЫЧИСЛЕНИЕ СТАНДАРТИЗИРОВАННЫХ ОСТАТКОВ (ДЛЯ GED)
    # ------------------------------------------------------------------------

    def _calculate_standardized_residuals(self, Aeq, x0, tolerances, balanced_flows):
        """
        Вычисление стандартизированных остатков для каждого измерения
        Формула: s_i = (x0_i - x_balanced_i) / σ_i, где σ_i = tolerance_i / 1.96

        Параметры:
        - Aeq: матрица ограничений (не используется, но оставлена для API)
        - x0: измеренные значения
        - tolerances: допуски измерений
        - balanced_flows: сбалансированные значения из solve()

        Возвращает: массив стандартизированных остатков
        """

        # Коэффициент для пересчёта допуска в стандартное отклонение (95% доверительный интервал)
        coef_delta = 1.96

        # Пересчитываем допуски в стандартные отклонения
        sigma = np.array(tolerances) / coef_delta

        # Извлекаем сбалансированные значения из результата solve()
        x_balanced = np.array([f['balanced_value'] for f in balanced_flows])

        # Вычисляем остатки (разница между измерением и балансом)
        residuals = x0 - x_balanced

        # Стандартизируем остатки (делим на стандартное отклонение)
        standardized_residuals = residuals / sigma

        # Конвертируем numpy типы в Python типы и возвращаем
        return to_python(standardized_residuals)

    # ------------------------------------------------------------------------
    # ПОЛНЫЙ ИТЕРАТИВНЫЙ АЛГОРИТМ GED (GROSS ERROR DETECTION)
    # ------------------------------------------------------------------------

    def find_gross_errors_full(self, flows, nodes, constraints=None, max_iterations=5):
        """
        Полный итеративный алгоритм GED (Global Evaluation of Data)


        """

        # Создаём копии данных, чтобы не изменять оригиналы
        current_flows = [flow.copy() for flow in flows]
        current_nodes = [node.copy() for node in nodes]

        # Список для хранения результатов всех итераций
        all_results = []

        # Список для хранения подозрительных потоков (уникальных)
        suspicious_flows = []

        # Множество для отслеживания ID уже найденных потоков (чтобы не было дубликатов)
        found_flow_ids = set()

        # Основной цикл итераций
        for iteration in range(max_iterations):

            # ШАГ 1: Решаем задачу балансировки с текущими данными
            result = self.solve(current_flows, current_nodes, constraints)

            # Если решение не найдено — выходим
            if result['status'] != 'success':
                break

            # Получаем значение глобального теста
            gtst = result.get('global_test', 1.0)

            # Сохраняем результат текущей итерации
            iteration_result = {
                'iteration': iteration + 1,
                'gtst': gtst,
                'is_consistent': result.get('is_consistent', True),
                'balanced_flows': result.get('balanced_flows', []),
                'suspicious_in_this_iteration': []
            }

            # ШАГ 2: Если GTst ≤ 1, данные согласованы → останавливаемся
            if gtst <= 1.0:
                iteration_result['message'] = 'Данные согласованы, грубых ошибок не найдено'
                all_results.append(iteration_result)
                break

            # ШАГ 3: GTst > 1 → ищем грубые ошибки

            # Получаем сбалансированные потоки
            balanced_flows = result['balanced_flows']

            # Строим матрицу Aeq для текущих данных
            Aeq = self._build_matrix(current_nodes, [f['id'] for f in current_flows], len(current_flows))

            # Извлекаем измеренные значения и допуски
            x0 = np.array([f['measured_value'] for f in current_flows])
            tols = np.array([f['tolerance'] for f in current_flows])

            # Вычисляем стандартизированные остатки
            standardized_residuals = self._calculate_standardized_residuals(
                Aeq, x0, tols, balanced_flows
            )

            # ШАГ 4: Находим поток с максимальным абсолютным остатком
            max_idx = np.argmax(np.abs(standardized_residuals))
            max_residual = standardized_residuals[max_idx]

            # Порог для обнаружения грубой ошибки
            # 2.5 соответствует 99% доверительному интервалу нормального распределения
            threshold = 2.5

            # ШАГ 5: Если превышает порог — найдена грубая ошибка
            if abs(max_residual) > threshold:
                flow_id = current_flows[max_idx]['id']

                # Проверяем, не добавляли ли уже этот поток в список
                if flow_id not in found_flow_ids:
                    # Добавляем ID в множество найденных
                    found_flow_ids.add(flow_id)

                    # Копируем подозрительный поток
                    suspicious_flow = current_flows[max_idx].copy()
                    suspicious_flow['standardized_residual'] = float(max_residual)
                    suspicious_flow['iteration_found'] = iteration + 1

                    # Добавляем в список подозрительных
                    suspicious_flows.append(suspicious_flow)

                # Сохраняем информацию о подозрительном потоке в результатах итерации
                iteration_result['suspicious_in_this_iteration'] = [{
                    'id': flow_id,
                    'standardized_residual': float(max_residual),
                    'iteration': iteration + 1
                }]
                iteration_result['message'] = f'Найден подозрительный поток: {flow_id} (остаток = {max_residual:.3f})'

                # ШАГ 6: Увеличиваем tolerance для найденного потока
                # Это уменьшает его влияние на следующих итерациях
                current_flows[max_idx]['tolerance'] = current_flows[max_idx]['tolerance'] * 10

            else:
                # Если порог не превышен — подозрительных потоков больше нет
                iteration_result['message'] = 'Подозрительных потоков не найдено'
                all_results.append(iteration_result)
                break

            # Добавляем результат итерации в общий список
            all_results.append(iteration_result)

        # Формируем и возвращаем итоговый результат
        return to_python({
            'suspicious_flows': suspicious_flows,  # Список подозрительных потоков
            'iterations': len(all_results),  # Количество выполненных итераций
            'final_gtst': all_results[-1]['gtst'] if all_results else 1.0,  # Финальное значение GTst
            'is_consistent_final': all_results[-1]['is_consistent'] if all_results else True,
            'iteration_details': all_results  # Детали всех итераций
        })

    # ------------------------------------------------------------------------
    # ОБНАРУЖЕНИЕ ГРУБЫХ ОШИБОК (УПРОЩЁННЫЙ ВЫЗОВ)
    # ------------------------------------------------------------------------

    def detect_gross_errors(self, flows, nodes, constraints=None):
        """
        Поиск грубых ошибок методом GED (с уникальными потоками)

        Это основной метод, который вызывается из API.
        Возвращает список подозрительных измерений.
        """

        # Вызываем полный итеративный алгоритм GED
        result = self.find_gross_errors_full(flows, nodes, constraints, max_iterations=5)

        # Формируем ответ в зависимости от того, найдены ли ошибки
        if result['suspicious_flows']:
            return to_python({
                'has_errors': True,  # Есть грубые ошибки
                'suspicious_flows': result['suspicious_flows'],  # Список подозрительных потоков
                'message': f"Обнаружено {len(result['suspicious_flows'])} подозрительных измерений",
                'details': result  # Детали для отладки
            })
        else:
            return to_python({
                'has_errors': False,  # Нет грубых ошибок
                'suspicious_flows': [],  # Пустой список
                'message': "Грубых ошибок не обнаружено",
                'details': result
            })

    # ------------------------------------------------------------------------
    # ПОСТРОЕНИЕ МАТРИЦЫ ОГРАНИЧЕНИЙ (Aeq)
    # ------------------------------------------------------------------------

    def _build_matrix(self, nodes: List[Dict], flow_ids: List[str], n: int):
        """
        Строит матрицу ограничений-равенств Aeq для балансовых уравнений узлов

        Параметры:
        - nodes: список узлов с уравнениями
        - flow_ids: список ID всех потоков
        - n: общее количество потоков

        Возвращает: матрицу Aeq размером (количество_уравнений × количество_потоков)

        Пример: для узла N1 с уравнениями X1 (+1), X2 (-1), X3 (-1)
        строка матрицы будет: [1, -1, -1, 0, 0, ...]
        """

        # Количество узлов = количество уравнений баланса
        m = len(nodes)

        # Инициализируем нулевую матрицу нужного размера
        Aeq = np.zeros((m, n))

        # Создаём словарь для быстрого поиска индекса потока по его ID
        # {flow_id: индекс_в_массиве_потоков}
        flow_to_idx = {fid: i for i, fid in enumerate(flow_ids)}

        # Перебираем все узлы (индекс узла, словарь с данными узла)
        for i, node in enumerate(nodes):
            # Получаем список уравнений для этого узла (ключ 'equations')
            # Если ключа нет, используем пустой список
            equations = node.get('equations', [])

            # Перебираем все уравнения текущего узла
            for eq in equations:
                flow_id = eq['flow_id']  # ID потока в уравнении
                sign = eq.get('sign', 1)  # Коэффициент (знак) потока, по умолчанию +1

                # Если такой поток существует в нашей системе
                if flow_id in flow_to_idx:
                    # Добавляем коэффициент в соответствующую ячейку матрицы
                    # Суммируем на случай, если поток несколько раз встречается в одном узле
                    Aeq[i, flow_to_idx[flow_id]] += sign

        # Возвращаем построенную матрицу
        return Aeq

    # ------------------------------------------------------------------------
    # ПОСТРОЕНИЕ МАТРИЦЫ ДЛЯ ДОПОЛНИТЕЛЬНЫХ ОГРАНИЧЕНИЙ
    # ------------------------------------------------------------------------

    def _build_constraints(self, constraints: List[Dict], flow_ids: List[str], n: int):
        """
        Строит матрицу и правую часть для дополнительных линейных ограничений

        Параметры:
        - constraints: список ограничений вида Σ(coef_i * flow_i) = rhs
        - flow_ids: список ID всех потоков
        - n: количество потоков

        Возвращает: (A_extra, b_extra) - матрица ограничений и правая часть
        """

        # Если нет ограничений, возвращаем None (сигнал об отсутствии)
        if not constraints:
            return None, None

        # Словарь для быстрого поиска индекса потока по ID
        flow_to_idx = {fid: i for i, fid in enumerate(flow_ids)}

        # Списки для строк матрицы и элементов правой части
        A_extra = []  # Каждая строка - вектор коэффициентов для одного ограничения
        b_extra = []  # Каждый элемент - правая часть ограничения (rhs)

        # Перебираем все дополнительные ограничения
        for constr in constraints:
            # Инициализируем нулевую строку для текущего ограничения
            row = np.zeros(n)

            # Перебираем члены в ограничении (сумма произведений коэффициентов на потоки)
            for term in constr['terms']:
                flow_id = term['flow_id']  # ID потока
                coeff = term['coefficient']  # Коэффициент перед потоком

                # Если поток существует в нашей системе
                if flow_id in flow_to_idx:
                    # Добавляем коэффициент в соответствующую позицию строки
                    row[flow_to_idx[flow_id]] = coeff

            # Добавляем правую часть ограничения (по умолчанию 0, если не указана)
            b_extra.append(constr.get('rhs', 0))

            # Добавляем сформированную строку в матрицу
            A_extra.append(row)

        # Преобразуем списки в массивы NumPy и возвращаем
        return np.array(A_extra), np.array(b_extra)