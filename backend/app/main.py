from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import BalanceRequest, BalanceResponse, BalancedFlow
from .qp_solver import BalanceSolver

app = FastAPI(title="Balance Reconciliation Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

solver = BalanceSolver()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/api/v1/reconcile", response_model=BalanceResponse)
async def reconcile_balance(request: BalanceRequest):
    flow_ids = {f.id for f in request.flows}
    for node in request.nodes:
        for eq in node.equations:
            if eq.flow_id not in flow_ids:
                raise HTTPException(status_code=400,
                                    detail=f"Поток {eq.flow_id} не найден в узле {node.id}")

    flows = [f.dict() for f in request.flows]
    nodes = [n.dict() for n in request.nodes]
    constraints = [c.dict() for c in request.constraints] if request.constraints else None

    result = solver.solve(flows, nodes, constraints)

    if result['status'] != 'success':
        raise HTTPException(status_code=400, detail=result.get('message', 'Ошибка решения'))

    return BalanceResponse(
        status=result['status'],
        balanced_flows=[BalancedFlow(**f) for f in result['balanced_flows']],
        max_disbalance=result['max_disbalance'],
        iterations=result['iterations'],
        global_test=result.get('global_test'),
        global_test_limit=result.get('global_test_limit'),
        global_test_original=result.get('global_test_original'),
        is_consistent=result.get('is_consistent'),
        degrees_of_freedom=result.get('degrees_of_freedom')
    )


@app.post("/api/v1/detect-errors")
async def detect_gross_errors(request: BalanceRequest):
    """
    Поиск грубых ошибок в измерениях методом GED
    """
    flow_ids = {f.id for f in request.flows}
    for node in request.nodes:
        for eq in node.equations:
            if eq.flow_id not in flow_ids:
                raise HTTPException(status_code=400,
                                    detail=f"Поток {eq.flow_id} не найден в узле {node.id}")

    flows = [f.dict() for f in request.flows]
    nodes = [n.dict() for n in request.nodes]
    constraints = [c.dict() for c in request.constraints] if request.constraints else None

    result = solver.detect_gross_errors(flows, nodes, constraints)

    return {
        "status": "success",
        "has_errors": result['has_errors'],
        "suspicious_flows": result['suspicious_flows'],
        "message": result['message'],
        "details": result['details']
    }
