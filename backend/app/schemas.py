from pydantic import BaseModel
from typing import List, Optional

class FlowInput(BaseModel):
    id: str
    name: str
    measured_value: float
    tolerance: float
    min_value: float = 0
    max_value: float = 10000

class EquationTerm(BaseModel):
    flow_id: str
    sign: int

class NodeInput(BaseModel):
    id: str
    name: str
    equations: List[EquationTerm]

class ConstraintTerm(BaseModel):
    flow_id: str
    coefficient: float

class ConstraintInput(BaseModel):
    terms: List[ConstraintTerm]
    rhs: float = 0

class BalanceRequest(BaseModel):
    flows: List[FlowInput]
    nodes: List[NodeInput]
    constraints: Optional[List[ConstraintInput]] = None

class BalancedFlow(BaseModel):
    id: str
    name: str
    original_value: float
    balanced_value: float
    correction: float
    relative_error: float

class BalanceResponse(BaseModel):
    status: str
    balanced_flows: List[BalancedFlow]
    max_disbalance: float
    iterations: int
    message: Optional[str] = None
    # Глобальный тест
    global_test: Optional[float] = None
    global_test_limit: Optional[float] = None
    global_test_original: Optional[float] = None
    is_consistent: Optional[bool] = None
    degrees_of_freedom: Optional[int] = None

