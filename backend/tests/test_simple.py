"""Простые тесты для проверки работоспособности"""

def test_import_schemas():
    """Проверка импорта моделей данных"""
    from app.schemas import FlowInput, NodeInput, EquationTerm, BalanceRequest
    print("✅ Модели данных импортированы успешно")
    return True

def test_import_solver():
    """Проверка импорта солвера"""
    from app.qp_solver import BalanceSolver
    print("✅ Солвер импортирован успешно")
    return True

def test_create_flow():
    """Проверка создания потока"""
    from app.schemas import FlowInput
    
    flow = FlowInput(
        id="X1",
        name="Тестовый поток",
        measured_value=10.5,
        tolerance=0.5
    )
    
    assert flow.id == "X1"
    assert flow.name == "Тестовый поток"
    assert flow.measured_value == 10.5
    assert flow.tolerance == 0.5
    print("✅ Поток создан успешно")

def test_create_node():
    """Проверка создания узла"""
    from app.schemas import EquationTerm, NodeInput
    
    term1 = EquationTerm(flow_id="X1", sign=1)
    term2 = EquationTerm(flow_id="X2", sign=-1)
    
    node = NodeInput(
        id="N1",
        name="Узел 1",
        equations=[term1, term2]
    )
    
    assert node.id == "N1"
    assert len(node.equations) == 2
    assert node.equations[0].flow_id == "X1"
    assert node.equations[0].sign == 1
    print("✅ Узел создан успешно")

def test_create_balance_request():
    """Проверка создания запроса на балансировку"""
    from app.schemas import FlowInput, EquationTerm, NodeInput, BalanceRequest
    
    flows = [
        FlowInput(id="X1", name="Поток 1", measured_value=10, tolerance=1),
        FlowInput(id="X2", name="Поток 2", measured_value=10, tolerance=1)
    ]
    
    nodes = [
        NodeInput(
            id="N1",
            name="Узел 1",
            equations=[
                EquationTerm(flow_id="X1", sign=1),
                EquationTerm(flow_id="X2", sign=-1)
            ]
        )
    ]
    
    request = BalanceRequest(flows=flows, nodes=nodes, constraints=None)
    
    assert len(request.flows) == 2
    assert len(request.nodes) == 1
    print("✅ Запрос создан успешно")

def test_solver_initialization():
    """Проверка инициализации солвера"""
    from app.qp_solver import BalanceSolver
    
    solver = BalanceSolver()
    assert solver is not None
    print("✅ Солвер инициализирован успешно")

def test_solver_solve_simple():
    """Проверка работы солвера на простой задаче"""
    from app.qp_solver import BalanceSolver
    
    solver = BalanceSolver()
    
    flows = [
        {"id": "X1", "name": "Поток 1", "measured_value": 10, "tolerance": 1},
        {"id": "X2", "name": "Поток 2", "measured_value": 10, "tolerance": 1}
    ]
    
    nodes = [
        {"id": "N1", "name": "Узел 1", "equations": [
            {"flow_id": "X1", "sign": 1},
            {"flow_id": "X2", "sign": -1}
        ]}
    ]
    
    result = solver.solve(flows, nodes, None)
    
    # Проверяем, что результат имеет ожидаемую структуру
    assert "status" in result
    print(f"✅ Солвер выполнен, статус: {result['status']}")

def run_all_tests():
    """Запуск всех тестов"""
    print("\n" + "="*50)
    print("ЗАПУСК ТЕСТОВ")
    print("="*50)
    
    tests = [
        ("Импорт моделей", test_import_schemas),
        ("Импорт солвера", test_import_solver),
        ("Создание потока", test_create_flow),
        ("Создание узла", test_create_node),
        ("Создание запроса", test_create_balance_request),
        ("Инициализация солвера", test_solver_initialization),
        ("Работа солвера", test_solver_solve_simple)
    ]
    
    passed = 0
    failed = 0
    
    for name, test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Тест '{name}' провален: {e}")
            failed += 1
    
    print("\n" + "="*50)
    print(f"РЕЗУЛЬТАТЫ: {passed} пройдено, {failed} провалено")
    print("="*50)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
