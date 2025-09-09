"""
数据流分析模块

本模块实现了多种数据流分析算法：
- 到达定值分析(Reaching Definitions)
- 活跃变量分析(Live Variable Analysis)  
- 可用表达式分析(Available Expressions)
- 使用变量分析(Use-Def Analysis)
"""

import networkx as nx
from typing import Dict, Set, List, Tuple, Any, Optional
import logging
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class Definition:
    """变量定义信息"""
    variable: str
    location: Any  # 定义位置
    block_id: str
    statement: Any
    
    def __hash__(self):
        return hash((self.variable, str(self.location), self.block_id))
    
    def __eq__(self, other):
        if not isinstance(other, Definition):
            return False
        return (self.variable == other.variable and 
                self.location == other.location and 
                self.block_id == other.block_id)

@dataclass 
class Use:
    """变量使用信息"""
    variable: str
    location: Any
    block_id: str
    statement: Any

class DataFlowAnalyzer:
    """数据流分析器"""
    
    def __init__(self, cfg: nx.DiGraph):
        """
        初始化数据流分析器
        
        Args:
            cfg: 控制流图
        """
        self.cfg = cfg
        
        # 到达定值分析结果
        self.reaching_defs_in: Dict[str, Set[Definition]] = {}
        self.reaching_defs_out: Dict[str, Set[Definition]] = {}
        self.gen_sets: Dict[str, Set[Definition]] = {}
        self.kill_sets: Dict[str, Set[Definition]] = {}
        
        # 活跃变量分析结果
        self.live_vars_in: Dict[str, Set[str]] = {}
        self.live_vars_out: Dict[str, Set[str]] = {}
        self.use_sets: Dict[str, Set[str]] = {}
        self.def_sets: Dict[str, Set[str]] = {}
        
        # 可用表达式分析结果
        self.avail_exprs_in: Dict[str, Set[str]] = {}
        self.avail_exprs_out: Dict[str, Set[str]] = {}
        self.expr_gen_sets: Dict[str, Set[str]] = {}
        self.expr_kill_sets: Dict[str, Set[str]] = {}
        
        # 辅助数据结构
        self.all_definitions: Set[Definition] = set()
        self.all_variables: Set[str] = set()
        self.all_expressions: Set[str] = set()
    
    def analyze(self) -> Dict[str, Any]:
        """
        执行完整的数据流分析
        
        Returns:
            Dict[str, Any]: 分析结果
        """
        logger.info("Starting data flow analysis...")
        
        # 1. 收集所有定义、使用和表达式
        self._collect_definitions_and_uses()
        
        # 2. 计算各种集合
        self._compute_gen_kill_sets()
        self._compute_use_def_sets()
        self._compute_expression_sets()
        
        # 3. 执行各种分析
        self.reaching_definitions_analysis()
        self.live_variables_analysis()
        self.available_expressions_analysis()
        
        logger.info("Data flow analysis completed")
        
        return {
            'reaching_definitions': {
                'in': self.reaching_defs_in,
                'out': self.reaching_defs_out
            },
            'live_variables': {
                'in': self.live_vars_in,
                'out': self.live_vars_out
            },
            'available_expressions': {
                'in': self.avail_exprs_in,
                'out': self.avail_exprs_out
            },
            'definitions': self.all_definitions,
            'variables': self.all_variables
        }
    
    def reaching_definitions_analysis(self):
        """到达定值分析 - 前向数据流分析"""
        logger.info("Running reaching definitions analysis...")
        
        # 初始化
        for node in self.cfg.nodes:
            self.reaching_defs_in[node] = set()
            self.reaching_defs_out[node] = set()
        
        # 工作列表算法
        worklist = list(self.cfg.nodes)
        iteration = 0
        
        while worklist:
            iteration += 1
            if iteration > 1000:  # 防止无限循环
                logger.warning("Reaching definitions analysis: max iterations reached")
                break
                
            node = worklist.pop(0)
            
            # 计算新的IN集合: IN[n] = ∪ OUT[p] for all predecessors p of n
            new_in = set()
            for pred in self.cfg.predecessors(node):
                new_in.update(self.reaching_defs_out[pred])
            
            # 计算新的OUT集合: OUT[n] = GEN[n] ∪ (IN[n] - KILL[n])
            new_out = self.gen_sets[node] | (new_in - self.kill_sets[node])
            
            # 检查是否有变化
            if new_in != self.reaching_defs_in[node] or new_out != self.reaching_defs_out[node]:
                self.reaching_defs_in[node] = new_in
                self.reaching_defs_out[node] = new_out
                
                # 将所有后继节点加入工作列表
                for succ in self.cfg.successors(node):
                    if succ not in worklist:
                        worklist.append(succ)
        
        logger.info(f"Reaching definitions analysis completed in {iteration} iterations")
    
    def live_variables_analysis(self):
        """活跃变量分析 - 后向数据流分析"""
        logger.info("Running live variables analysis...")
        
        # 初始化
        for node in self.cfg.nodes:
            self.live_vars_in[node] = set()
            self.live_vars_out[node] = set()
        
        # 工作列表算法 (后向分析)
        worklist = list(self.cfg.nodes)
        iteration = 0
        
        while worklist:
            iteration += 1
            if iteration > 1000:
                logger.warning("Live variables analysis: max iterations reached")
                break
                
            node = worklist.pop(0)
            
            # 计算新的OUT集合: OUT[n] = ∪ IN[s] for all successors s of n
            new_out = set()
            for succ in self.cfg.successors(node):
                new_out.update(self.live_vars_in[succ])
            
            # 计算新的IN集合: IN[n] = USE[n] ∪ (OUT[n] - DEF[n])
            new_in = self.use_sets[node] | (new_out - self.def_sets[node])
            
            # 检查是否有变化
            if new_in != self.live_vars_in[node] or new_out != self.live_vars_out[node]:
                self.live_vars_in[node] = new_in
                self.live_vars_out[node] = new_out
                
                # 将所有前驱节点加入工作列表
                for pred in self.cfg.predecessors(node):
                    if pred not in worklist:
                        worklist.append(pred)
        
        logger.info(f"Live variables analysis completed in {iteration} iterations")
    
    def available_expressions_analysis(self):
        """可用表达式分析 - 前向数据流分析"""
        logger.info("Running available expressions analysis...")
        
        # 初始化 - 除了入口节点，所有节点的IN集合都是全集
        entry_nodes = [n for n in self.cfg.nodes if self.cfg.nodes[n].get('type') == 'entry']
        
        for node in self.cfg.nodes:
            if node in entry_nodes:
                self.avail_exprs_in[node] = set()
            else:
                self.avail_exprs_in[node] = self.all_expressions.copy()
            self.avail_exprs_out[node] = set()
        
        # 工作列表算法
        worklist = list(self.cfg.nodes)
        iteration = 0
        
        while worklist:
            iteration += 1
            if iteration > 1000:
                logger.warning("Available expressions analysis: max iterations reached")
                break
                
            node = worklist.pop(0)
            
            # 计算新的IN集合: IN[n] = ∩ OUT[p] for all predecessors p of n
            new_in = self.all_expressions.copy()
            for pred in self.cfg.predecessors(node):
                new_in.intersection_update(self.avail_exprs_out[pred])
            
            # 如果是入口节点，IN集合为空
            if node in entry_nodes:
                new_in = set()
            
            # 计算新的OUT集合: OUT[n] = GEN[n] ∪ (IN[n] - KILL[n])
            new_out = self.expr_gen_sets[node] | (new_in - self.expr_kill_sets[node])
            
            # 检查是否有变化
            if new_in != self.avail_exprs_in[node] or new_out != self.avail_exprs_out[node]:
                self.avail_exprs_in[node] = new_in
                self.avail_exprs_out[node] = new_out
                
                # 将所有后继节点加入工作列表
                for succ in self.cfg.successors(node):
                    if succ not in worklist:
                        worklist.append(succ)
        
        logger.info(f"Available expressions analysis completed in {iteration} iterations")
    
    def _collect_definitions_and_uses(self):
        """收集所有变量定义和使用"""
        logger.info("Collecting definitions and uses...")
        
        for node_id in self.cfg.nodes:
            node_data = self.cfg.nodes[node_id]
            
            # 模拟从基本块中提取定义和使用
            # 实际实现中应该分析AST节点
            variables = node_data.get('variables', [])
            for var in variables:
                self.all_variables.add(var)
                
                # 简化处理：假设每个变量在每个块中都有一个定义
                definition = Definition(
                    variable=var,
                    location=node_data.get('location'),
                    block_id=node_id,
                    statement=None
                )
                self.all_definitions.add(definition)
    
    def _compute_gen_kill_sets(self):
        """计算到达定值分析的GEN和KILL集合"""
        logger.info("Computing GEN and KILL sets for reaching definitions...")
        
        for node_id in self.cfg.nodes:
            self.gen_sets[node_id] = set()
            self.kill_sets[node_id] = set()
            
            node_data = self.cfg.nodes[node_id]
            variables = node_data.get('variables', [])
            
            # GEN集合：在此基本块中生成的定义
            for var in variables:
                definition = Definition(
                    variable=var,
                    location=node_data.get('location'),
                    block_id=node_id,
                    statement=None
                )
                self.gen_sets[node_id].add(definition)
            
            # KILL集合：此基本块杀死的定义（同一变量的其他定义）
            for var in variables:
                for def_item in self.all_definitions:
                    if def_item.variable == var and def_item.block_id != node_id:
                        self.kill_sets[node_id].add(def_item)
    
    def _compute_use_def_sets(self):
        """计算活跃变量分析的USE和DEF集合"""
        logger.info("Computing USE and DEF sets for live variables...")
        
        for node_id in self.cfg.nodes:
            self.use_sets[node_id] = set()
            self.def_sets[node_id] = set()
            
            node_data = self.cfg.nodes[node_id]
            variables = node_data.get('variables', [])
            
            # 简化处理：假设每个变量既被使用也被定义
            for var in variables:
                self.use_sets[node_id].add(var)
                self.def_sets[node_id].add(var)
    
    def _compute_expression_sets(self):
        """计算可用表达式分析的GEN和KILL集合"""
        logger.info("Computing expression GEN and KILL sets...")
        
        # 简化处理：生成一些示例表达式
        for node_id in self.cfg.nodes:
            self.expr_gen_sets[node_id] = set()
            self.expr_kill_sets[node_id] = set()
            
            node_data = self.cfg.nodes[node_id]
            variables = node_data.get('variables', [])
            
            # 为每对变量生成表达式
            var_list = list(variables)
            for i, var1 in enumerate(var_list):
                for j, var2 in enumerate(var_list[i+1:], i+1):
                    expr = f"{var1} + {var2}"
                    self.all_expressions.add(expr)
                    self.expr_gen_sets[node_id].add(expr)
    
    def get_reaching_definitions(self, node_id: str, variable: str) -> Set[Definition]:
        """获取到达指定节点的变量定义"""
        reaching_defs = set()
        for definition in self.reaching_defs_in.get(node_id, set()):
            if definition.variable == variable:
                reaching_defs.add(definition)
        return reaching_defs
    
    def is_variable_live(self, node_id: str, variable: str) -> bool:
        """检查变量在指定节点是否活跃"""
        return variable in self.live_vars_out.get(node_id, set())
    
    def get_available_expressions(self, node_id: str) -> Set[str]:
        """获取在指定节点可用的表达式"""
        return self.avail_exprs_in.get(node_id, set()).copy()
    
    def find_def_use_chains(self) -> Dict[Definition, Set[str]]:
        """构建定义-使用链"""
        def_use_chains = defaultdict(set)
        
        for node_id in self.cfg.nodes:
            # 对于每个使用
            for used_var in self.use_sets.get(node_id, set()):
                # 找到所有到达的定义
                reaching_defs = self.get_reaching_definitions(node_id, used_var)
                for definition in reaching_defs:
                    def_use_chains[definition].add(node_id)
        
        return dict(def_use_chains)
    
    def find_use_def_chains(self) -> Dict[str, Set[Definition]]:
        """构建使用-定义链"""
        use_def_chains = defaultdict(set)
        
        for node_id in self.cfg.nodes:
            for used_var in self.use_sets.get(node_id, set()):
                use_key = f"{node_id}:{used_var}"
                reaching_defs = self.get_reaching_definitions(node_id, used_var)
                use_def_chains[use_key] = reaching_defs
        
        return dict(use_def_chains)
    
    def detect_uninitialized_variables(self) -> Set[Tuple[str, str]]:
        """检测未初始化的变量使用"""
        uninitialized = set()
        
        for node_id in self.cfg.nodes:
            for used_var in self.use_sets.get(node_id, set()):
                reaching_defs = self.get_reaching_definitions(node_id, used_var)
                if not reaching_defs:
                    uninitialized.add((node_id, used_var))
        
        return uninitialized
    
    def detect_dead_code(self) -> Set[str]:
        """检测死代码（定义了但从未使用的变量）"""
        dead_definitions = set()
        def_use_chains = self.find_def_use_chains()
        
        for definition in self.all_definitions:
            if definition not in def_use_chains or not def_use_chains[definition]:
                dead_definitions.add(definition.block_id)
        
        return dead_definitions
    
    def print_analysis_results(self):
        """打印分析结果统计"""
        print("=== Data Flow Analysis Results ===")
        print(f"Total variables: {len(self.all_variables)}")
        print(f"Total definitions: {len(self.all_definitions)}")
        print(f"Total expressions: {len(self.all_expressions)}")
        
        print(f"\nUninitialized variables: {len(self.detect_uninitialized_variables())}")
        print(f"Dead code blocks: {len(self.detect_dead_code())}")
        
        print("\nReaching definitions summary:")
        for node_id in sorted(self.cfg.nodes):
            in_count = len(self.reaching_defs_in.get(node_id, set()))
            out_count = len(self.reaching_defs_out.get(node_id, set()))
            print(f"  {node_id}: IN={in_count}, OUT={out_count}")
        
        print("\nLive variables summary:")
        for node_id in sorted(self.cfg.nodes):
            in_count = len(self.live_vars_in.get(node_id, set()))
            out_count = len(self.live_vars_out.get(node_id, set()))
            print(f"  {node_id}: IN={in_count}, OUT={out_count}")


class PointerAnalyzer:
    """指针分析器 - 处理C语言指针的复杂性"""
    
    def __init__(self, cfg: nx.DiGraph):
        self.cfg = cfg
        self.points_to: Dict[str, Set[str]] = defaultdict(set)
        self.aliases: Dict[str, Set[str]] = defaultdict(set)
    
    def analyze_pointers(self) -> Dict[str, Any]:
        """执行指针分析"""
        logger.info("Starting pointer analysis...")
        
        # 收集指针相关操作
        self._collect_pointer_operations()
        
        # 计算指向关系
        self._compute_points_to_sets()
        
        # 计算别名关系  
        self._compute_alias_sets()
        
        logger.info("Pointer analysis completed")
        
        return {
            'points_to': dict(self.points_to),
            'aliases': dict(self.aliases)
        }
    
    def _collect_pointer_operations(self):
        """收集指针相关操作"""
        # 简化实现：从节点变量中识别指针操作
        for node_id in self.cfg.nodes:
            node_data = self.cfg.nodes[node_id]
            variables = node_data.get('variables', [])
            
            for var in variables:
                # 简单启发式：带*的是指针解引用，带&的是取地址
                if var.startswith('*'):
                    base_var = var[1:]
                    if base_var in variables:
                        self.points_to[base_var].add(var)
                elif var.startswith('&'):
                    target_var = var[1:]
                    self.points_to[var].add(target_var)
    
    def _compute_points_to_sets(self):
        """计算指向集合"""
        # 使用不动点算法
        changed = True
        iterations = 0
        
        while changed and iterations < 100:
            changed = False
            iterations += 1
            
            for ptr, targets in self.points_to.items():
                old_size = len(targets)
                
                # 传播指向关系
                for target in targets.copy():
                    if target in self.points_to:
                        targets.update(self.points_to[target])
                
                if len(targets) > old_size:
                    changed = True
    
    def _compute_alias_sets(self):
        """计算别名集合"""
        # 如果两个指针指向相同的内存位置，它们是别名
        all_pointers = set(self.points_to.keys())
        
        for ptr1 in all_pointers:
            for ptr2 in all_pointers:
                if ptr1 != ptr2:
                    # 如果指向的目标有交集，则可能是别名
                    if self.points_to[ptr1] & self.points_to[ptr2]:
                        self.aliases[ptr1].add(ptr2)
                        self.aliases[ptr2].add(ptr1)
    
    def may_alias(self, var1: str, var2: str) -> bool:
        """检查两个变量是否可能是别名"""
        return var2 in self.aliases.get(var1, set())
    
    def points_to_set(self, pointer: str) -> Set[str]:
        """获取指针的指向集合"""
        return self.points_to.get(pointer, set()).copy()


class StructHandler:
    """结构体处理器 - 处理结构体字段访问"""
    
    def __init__(self):
        self.struct_defs: Dict[str, Dict[str, Any]] = {}
        self.field_accesses: List[Tuple[str, str, str]] = []  # (base, field, location)
    
    def add_struct_definition(self, struct_name: str, fields: Dict[str, Any]):
        """添加结构体定义"""
        self.struct_defs[struct_name] = fields
    
    def add_field_access(self, base: str, field: str, location: str):
        """添加字段访问"""
        self.field_accesses.append((base, field, location))
    
    def get_field_type(self, struct_name: str, field_name: str) -> Optional[Any]:
        """获取结构体字段类型"""
        if struct_name in self.struct_defs:
            return self.struct_defs[struct_name].get(field_name)
        return None
    
    def analyze_field_dependencies(self) -> Dict[str, Set[str]]:
        """分析字段依赖关系"""
        dependencies = defaultdict(set)
        
        for base, field, location in self.field_accesses:
            field_key = f"{base}.{field}"
            dependencies[field_key].add(location)
        
        return dict(dependencies)