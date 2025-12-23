from dataclasses import dataclass, field
from typing import List, Dict, Any, Set
from enum import Enum


class DependencyType(Enum):
    """依赖关系类型"""
    ASSIGNMENT = "assignment"  # 赋值关系: a = b
    CONDITION = "condition"    # 条件依赖: if (a)
    ARITHMETIC = "arithmetic"  # 算术运算: a = b + c
    POINTER = "pointer"        # 指针引用: a = *b
    FUNCTION_CALL = "function_call"  # 函数参数传递
    RETURN = "return"          # 返回值依赖
    COMPARISON = "comparison"  # 比较运算: a == b


@dataclass
class VariableNode:
    """范畴对象：变量"""
    name: str
    type: str
    is_pointer: bool
    is_const: bool
    scope: str  # 所属函数或全局
    references: List[str] = field(default_factory=list)  # 态射：被引用/赋值的位置
    # 依赖关系
    depends_on: Dict[str, Set[DependencyType]] = field(default_factory=dict)  # var_name -> {dependency_types}
    dependents: Dict[str, Set[DependencyType]] = field(default_factory=dict)  # var_name -> {dependency_types}


@dataclass
class DependencyRelation:
    """变量间依赖关系"""
    source: str      # 源变量
    target: str      # 目标变量
    dep_type: DependencyType  # 依赖类型
    context: str     # 上下文信息（如所在函数）
    line_number: int = 0     # 行号


@dataclass
class FunctionNode:
    """范畴对象：函数"""
    name: str
    return_type: str
    parameters: List[Dict[str, str]]  # 参数列表
    calls: List[str] = field(default_factory=list)  # 态射：调用了哪些函数
    called_by: List[str] = field(default_factory=list)  # 态射：被哪些函数调用
    vars_accessed: List[str] = field(default_factory=list)  # 态射：访问了哪些变量
    # 变量定义
    defined_vars: List[str] = field(default_factory=list)  # 函数内定义的变量


@dataclass
class CategoryContext:
    """上下文范畴：包含所有对象及态射关系"""
    variables: Dict[str, VariableNode]
    functions: Dict[str, FunctionNode]
    anchors: Dict[str, str]  # 语义锚点：变量名 -> 业务含义
    # 新增：依赖关系集合
    variable_dependencies: List[DependencyRelation] = field(default_factory=list)
    # 函数调用关系
    function_calls: List[tuple] = field(default_factory=list)  # (caller, callee) pairs
