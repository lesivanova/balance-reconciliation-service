import numpy as np
from scipy.optimize import minimize, Bounds
from scipy import stats
from scipy.linalg import pinv
from typing import List, Dict, Optional


class BalanceSolver:
    
    def calculate_global_test(self, Aeq, x0, tolerances, is_measured=None):
        """
        Расчет глобального теста (Global Test)
        """
        n = len(x0)
        m = Aeq.shape[0]

        coef_delta = 1.96
        xStd = np.array(tolerances) / coef_delta

        if is_measured is None:
            is_measured = np.ones(n)

        max_x0 = np.max(np.abs(x0)) if len(x0) > 0 else 1.0
        for i in range(n):
            if is_measured[i] == 0:
                xStd[i] = 100 * max_x0

        xSigma = np.diag(xStd ** 2)
        r = Aeq @ x0
        V = Aeq @ xSigma @ Aeq.T

        try:
            GT_original = r.T @ pinv(V) @ r
        except:
            GT_original = 0.0

        alpha = 0.05
        degrees_of_freedom = m
        GT_limit = stats.chi2.ppf(1 - alpha, degrees_of_freedom)

        if GT_original == 0 and GT_limit == 0:
            GTst = 0.0
        else:
            GTst = GT_original / GT_limit

        is_consistent = GT_original <= GT_limit

        return {
            'GTst': float(GTst),
            'GT_original': float(GT_original),
            'GT_limit': float(GT_limit),
            'degrees_of_freedom': degrees_of_freedom,
            'is_consistent': is_consistent,
        }

    def _calculate_standardized_residuals(self, Aeq, x0, tolerances, balanced_flows):
        """
        Вычисление стандартизированных остатков для каждого измерения
        
        Стандартизированный остаток = (x0 - x_balanced) / σ
        где σ = tolerance / 1.96
        """
        n = len(x0)
        coef_delta = 1.96
        
        # Стандартные отклонения
        sigma = np.array(tolerances) / coef_delta
        
        # Сбалансированные значения
        x_balanced = np.array([f['balanced_value'] for f in balanced_flows])
        
        # Остатки
        residuals = x0 - x_balanced
        
        # Стандартизированные остатки
        standardized_residuals = residuals / sigma
        
        return standardized_residuals

    def find_gross_errors(self, flows, nodes, constraints=None, max_iterations=10):
        """
        Поиск грубых ошибок методом GED (Global Evaluation of Data)
        
        Алгоритм:
        1. Решаем задачу балансировки
        2. Вычисляем глобальный тест
        3. Если GTst > 1, ищем измерения с наибольшими остатками
        4. Помечаем подозрительные измерения
        5. Повторяем, исключая подозрительные измерения (или помечая их)
        
        Возвращает:
        - suspicious_flows: список подозрительных потоков
        - iterations: количество итераций
        - final_gtst: финальное значение глобального теста
        - all_results: результаты всех итераций
        """
        
        # Копируем данные, чтобы не изменять оригинал
        current_flows = [flow.copy() for flow in flows]
        current_nodes = [node.copy() for node in nodes]
        
        all_results = []
        suspicious_flows = []
        
        for iteration in range(max_iterations):
            # 1. Решаем задачу с текущими данными
            result = self.solve(current_flows, current_nodes, constraints)
            
            if result['status'] != 'success':
                break
            
            gtst = result.get('global_test', 1.0)
            
            # Сохраняем результат итерации
            iteration_result = {
                'iteration': iteration + 1,
                'gtst': gtst,
                'is_consistent': result.get('is_consistent', True),
                'balanced_flows': result.get('balanced_flows', []),
                'suspicious_in_this_iteration': []
            }
            
            # 2. Если данные согласованы с моделью (GTst ≤ 1) — останавливаемся
            if gtst <= 1.0:
                iteration_result['message'] = 'Данные согласованы, грубых ошибок не найдено'
                all_results.append(iteration_result)
                break
            
            # 3. GTst > 1 → ищем грубые ошибки
            balanced_flows = result['balanced_flows']
            
            # Вычисляем стандартизированные остатки для каждого потока
            Aeq = self._build_matrix(current_nodes, [f['id'] for f in current_flows], len(current_flows))
            x0 = np.array([f['measured_value'] for f in current_flows])
            tols = np.array([f['tolerance'] for f in current_flows])
            
            standardized_residuals = self._calculate_standardized_residuals(
                Aeq, x0, tols, balanced_flows
            )
            
            # 4. Находим поток с максимальным абсолютным остатком
            max_idx = np.argmax(np.abs(standardized_residuals))
            max_residual = standardized_residuals[max_idx]
            
            # Порог для обнаружения грубой ошибки (обычно 2.5 или 3.0)
            threshold = 2.5
            
            if abs(max_residual) > threshold:
                # Найден подозрительный поток
                suspicious_flow = current_flows[max_idx].copy()
                suspicious_flow['standardized_residual'] = float(max_residual)
                suspicious_flow['iteration_found'] = iteration + 1
                
                suspicious_flows.append(suspicious_flow)
                iteration_result['suspicious_in_this_iteration'] = [suspicious_flow]
                iteration_result['message'] = f'Найден подозрительный поток: {suspicious_flow["id"]} (остаток = {max_residual:.3f})'
                
                # Помечаем поток как подозрительный (увеличиваем tolerance)
                current_flows[max_idx]['tolerance'] = current_flows[max_idx]['tolerance'] * 10
                
            else:
                iteration_result['message'] = 'Подозрительных потоков не найдено'
                all_results.append(iteration_result)
                break
            
            all_results.append(iteration_result)
        
        return {
            'suspicious_flows': suspicious_flows,
            'iterations': len(all_results),
            'final_gtst': all_results[-1]['gtst'] if all_results else 1.0,
            'is_consistent_final': all_results[-1]['is_consistent'] if all_results else True,
            'iteration_details': all_results
        }

    def detect_gross_errors(self, flows, nodes, constraints=None):
        """
        Упрощенная версия поиска грубых ошибок
        Возвращает список подозрительных измерений
        """
        result = self.find_gross_errors(flows, nodes, constraints, max_iterations=5)
        
        if result['suspicious_flows']:
            return {
                'has_errors': True,
                'suspicious_flows': result['suspicious_flows'],
                'message': f"Обнаружено {len(result['suspicious_flows'])} подозрительных измерений",
                'details': result
            }
        else:
            return {
                'has_errors': False,
                'suspicious_flows': [],
                'message': "Грубых ошибок не обнаружено",
                'details': result
            }

    def solve(self, flows: List[Dict], nodes: List[Dict], constraints: Optional[List[Dict]] = None):
        n = len(flows)
        flow_ids = [f['id'] for f in flows]

        x0 = np.array([f['measured_value'] for f in flows])
        tols = np.array([f['tolerance'] for f in flows])
        lb = np.array([f.get('min_value', 0) for f in flows])
        ub = np.array([f.get('max_value', 10000) for f in flows])

        Aeq = self._build_matrix(nodes, flow_ids, n)
        beq = np.zeros(len(nodes))

        inv_tols = np.zeros(n)
        for i, tol in enumerate(tols):
            if tol > 0:
                inv_tols[i] = 1.0 / tol

        H = np.diag(inv_tols ** 2)
        f = -H @ x0

        if constraints:
            A_extra, b_extra = self._build_constraints(constraints, flow_ids, n)
            if A_extra is not None:
                Aeq = np.vstack([Aeq, A_extra])
                beq = np.hstack([beq, b_extra])

        try:
            cons = {'type': 'eq', 'fun': lambda x: Aeq @ x - beq}
            bounds = Bounds(lb, ub)

            def objective(x):
                return 0.5 * x @ H @ x + f @ x

            result = minimize(objective, x0, method='SLSQP',
                              constraints=cons, bounds=bounds,
                              options={'maxiter': 500, 'disp': False})

            if result.success:
                balances = Aeq[:len(nodes)] @ result.x
                max_disbalance = float(np.max(np.abs(balances)))

                balanced_flows = []
                for i, flow in enumerate(flows):
                    balanced_flows.append({
                        'id': flow['id'],
                        'name': flow['name'],
                        'original_value': float(x0[i]),
                        'balanced_value': float(result.x[i]),
                        'correction': float(result.x[i] - x0[i]),
                        'relative_error': abs(result.x[i] - x0[i]) / x0[i] * 100 if x0[i] != 0 else 0
                    })

                # Глобальный тест
                is_measured = np.ones(n)
                gt_result = self.calculate_global_test(Aeq, x0, tols, is_measured)

                # Вычисляем стандартизированные остатки
                try:
                    residuals = self._calculate_standardized_residuals(Aeq, x0, tols, balanced_flows)
                    standardized_residuals = residuals.tolist()
                except:
                    standardized_residuals = []

                return {
                    'status': 'success',
                    'balanced_flows': balanced_flows,
                    'max_disbalance': max_disbalance,
                    'iterations': result.nit,
                    'global_test': gt_result['GTst'],
                    'global_test_limit': gt_result['GT_limit'],
                    'global_test_original': gt_result['GT_original'],
                    'is_consistent': gt_result['is_consistent'],
                    'degrees_of_freedom': gt_result['degrees_of_freedom'],
                    'standardized_residuals': standardized_residuals
                }
            else:
                return {'status': 'failed', 'message': 'Решение не найдено'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _build_matrix(self, nodes: List[Dict], flow_ids: List[str], n: int):
        m = len(nodes)
        Aeq = np.zeros((m, n))
        flow_to_idx = {fid: i for i, fid in enumerate(flow_ids)}

        for i, node in enumerate(nodes):
            for eq in node.get('equations', []):
                flow_id = eq['flow_id']
                sign = eq.get('sign', 1)
                if flow_id in flow_to_idx:
                    Aeq[i, flow_to_idx[flow_id]] += sign
        return Aeq

    def _build_constraints(self, constraints: List[Dict], flow_ids: List[str], n: int):
        if not constraints:
            return None, None

        flow_to_idx = {fid: i for i, fid in enumerate(flow_ids)}
        A_extra = []
        b_extra = []

        for constr in constraints:
            row = np.zeros(n)
            for term in constr['terms']:
                flow_id = term['flow_id']
                coeff = term['coefficient']
                if flow_id in flow_to_idx:
                    row[flow_to_idx[flow_id]] = coeff
            b_extra.append(constr.get('rhs', 0))
            A_extra.append(row)

        return np.array(A_extra), np.array(b_extra)
