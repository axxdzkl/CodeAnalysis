"""
函数调用图(Call Graph)构建模块

本模块实现了C语言函数调用图的构建功能，包括：
- 函数定义收集
- 直接函数调用分析  
- 函数指针调用分析
- 递归调用检测
"""

import clang.cindex
from clang.cindex import CursorKind, TypeKind
import networkx as nx
from typing import Dict, Set, List, Any, Optional
import logging
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class Function:
    """函数信息"""
    name: str
    location: Any
    return_type: str
    parameters: List[tuple]
    is_definition: bool
    is_static: bool

@dataclass
class FunctionCall:
    """函数调用信息"""
    caller: str
    callee: str
    location: Any
    call_type: str
    arguments: List[str]

class CallGraphBuilder:
    """函数调用图构建器"""
    
    def __init__(self, tu: clang.cindex.TranslationUnit):
        self.tu = tu
        self.call_graph = nx.DiGraph()
        self.functions: Dict[str, Function] = {}
        self.function_calls: List[FunctionCall] = []
        self.stats = {
            'total_functions': 0,
            'defined_functions': 0,
            'direct_calls': 0,
            'indirect_calls': 0,
            'recursive_calls': 0
        }
    
    def build_call_graph(self) -> nx.DiGraph:
        """构建函数调用图"""
        logger.info("Building function call graph...")
        
        self._collect_function_definitions()
        self._analyze_function_calls()
        self._build_graph()
        self._detect_recursive_calls()
        self._compute_statistics()
        
        logger.info(f"Call graph built with {self.call_graph.number_of_nodes()} functions")
        return self.call_graph
    
    def _collect_function_definitions(self):
        """收集所有函数定义和声明"""
        def visit_node(node, current_function=None):
            if node.kind == CursorKind.FUNCTION_DECL:
                func_info = self._extract_function_info(node)
                self.functions[func_info.name] = func_info
                self.call_graph.add_node(func_info.name, function_info=func_info)
                
                if func_info.is_definition:
                    for child in node.get_children():
                        if child.kind == CursorKind.COMPOUND_STMT:
                            visit_node(child, func_info.name)
            elif node.kind == CursorKind.CALL_EXPR and current_function:
                self._analyze_call_expression(node, current_function)
            elif current_function:
                for child in node.get_children():
                    visit_node(child, current_function)
            else:
                for child in node.get_children():
                    visit_node(child)
        
        visit_node(self.tu.cursor)
        logger.info(f"Found {len(self.functions)} functions")
    
    def _extract_function_info(self, func_node: Any) -> Function:
        """提取函数信息"""
        name = func_node.spelling
        location = func_node.location
        return_type = func_node.result_type.spelling
        is_definition = func_node.is_definition()
        is_static = func_node.storage_class == clang.cindex.StorageClass.STATIC
        
        parameters = []
        for child in func_node.get_children():
            if child.kind == CursorKind.PARM_DECL:
                param_name = child.spelling or f"param_{len(parameters)}"
                param_type = child.type.spelling
                parameters.append((param_name, param_type))
        
        return Function(name, location, return_type, parameters, is_definition, is_static)
    
    def _analyze_call_expression(self, call_expr: Any, caller: str):
        """分析单个函数调用表达式"""
        callee = self._get_callee_name(call_expr)
        
        if callee:
            arguments = []
            children = list(call_expr.get_children())
            
            for arg_node in children[1:]:
                arg_text = self._get_node_text(arg_node)
                arguments.append(arg_text)
            
            call_type = self._determine_call_type(call_expr, callee)
            
            call_info = FunctionCall(caller, callee, call_expr.location, call_type, arguments)
            self.function_calls.append(call_info)
    
    def _get_callee_name(self, call_expr: Any) -> Optional[str]:
        """获取被调用函数名"""
        children = list(call_expr.get_children())
        if not children:
            return None
        
        first_child = children[0]
        
        if first_child.kind == CursorKind.DECL_REF_EXPR:
            return first_child.spelling
        elif first_child.kind == CursorKind.MEMBER_REF_EXPR:
            return first_child.spelling
        else:
            return self._get_node_text(first_child)
    
    def _determine_call_type(self, call_expr: Any, callee: str) -> str:
        """确定调用类型"""
        children = list(call_expr.get_children())
        if not children:
            return 'unknown'
        
        first_child = children[0]
        if first_child.kind == CursorKind.DECL_REF_EXPR:
            return 'direct'
        else:
            return 'indirect'
    
    def _get_node_text(self, node: Any) -> str:
        """获取AST节点的文本表示"""
        try:
            if hasattr(node, 'extent') and node.extent:
                start = node.extent.start
                end = node.extent.end
                
                with open(start.file.name, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    
                if start.line == end.line:
                    line = lines[start.line - 1]
                    return line[start.column - 1:end.column - 1]
        except:
            pass
        
        return node.spelling or str(node.kind)
    
    def _build_graph(self):
        """构建调用图"""
        for call in self.function_calls:
            if call.callee in self.functions:
                self.call_graph.add_edge(
                    call.caller, call.callee,
                    call_info=call,
                    call_type=call.call_type
                )
    
    def _detect_recursive_calls(self):
        """检测递归调用"""
        direct_recursive = set()
        for node in self.call_graph.nodes:
            if self.call_graph.has_edge(node, node):
                direct_recursive.add(node)
        
        strongly_connected = list(nx.strongly_connected_components(self.call_graph))
        indirect_recursive = set()
        
        for component in strongly_connected:
            if len(component) > 1:
                indirect_recursive.update(component)
        
        for node in self.call_graph.nodes:
            is_recursive = node in direct_recursive or node in indirect_recursive
            self.call_graph.nodes[node]['is_recursive'] = is_recursive
        
        self.stats['recursive_calls'] = len(direct_recursive) + len(indirect_recursive)
    
    def _compute_statistics(self):
        """计算统计信息"""
        self.stats['total_functions'] = len(self.functions)
        self.stats['defined_functions'] = sum(1 for f in self.functions.values() if f.is_definition)
        self.stats['direct_calls'] = sum(1 for c in self.function_calls if c.call_type == 'direct')
        self.stats['indirect_calls'] = sum(1 for c in self.function_calls if c.call_type != 'direct')
    
    def get_callers(self, function_name: str) -> Set[str]:
        """获取调用指定函数的函数列表"""
        return set(self.call_graph.predecessors(function_name))
    
    def get_callees(self, function_name: str) -> Set[str]:
        """获取指定函数调用的函数列表"""
        return set(self.call_graph.successors(function_name))
    
    def compute_function_metrics(self, function_name: str) -> Dict[str, Any]:
        """计算函数的调用图指标"""
        if function_name not in self.call_graph:
            return {}
        
        in_degree = self.call_graph.in_degree(function_name)
        out_degree = self.call_graph.out_degree(function_name)
        fan_in = len(self.get_callers(function_name))
        fan_out = len(self.get_callees(function_name))
        
        return {
            'in_degree': in_degree,
            'out_degree': out_degree,
            'fan_in': fan_in,
            'fan_out': fan_out,
            'is_recursive': self.call_graph.nodes[function_name].get('is_recursive', False)
        }
    
    def print_call_graph_summary(self):
        """打印调用图摘要"""
        print("=== Function Call Graph Summary ===")
        print(f"Total functions: {self.stats['total_functions']}")
        print(f"Defined functions: {self.stats['defined_functions']}")
        print(f"Direct calls: {self.stats['direct_calls']}")
        print(f"Indirect calls: {self.stats['indirect_calls']}")
        print(f"Recursive functions: {self.stats['recursive_calls']}")
        print(f"Graph nodes: {self.call_graph.number_of_nodes()}")
        print(f"Graph edges: {self.call_graph.number_of_edges()}")