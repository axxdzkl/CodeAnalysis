"""
程序依赖图(PDG)构建模块

本模块实现了程序依赖图的构建，包括：
- 控制依赖分析
- 数据依赖分析
- 支配树构建
- 支配边界计算
- PDG可视化
"""

import networkx as nx
from typing import Dict, Set, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class DependencyEdge:
    """依赖边信息"""
    source: str
    target: str
    dep_type: str  # 'control' 或 'data'
    variable: Optional[str] = None  # 数据依赖时的变量名
    condition: Optional[str] = None  # 控制依赖时的条件
    
    def __hash__(self):
        return hash((self.source, self.target, self.dep_type, self.variable))

class PDGBuilder:
    """程序依赖图构建器"""
    
    def __init__(self, cfg: nx.DiGraph, dataflow_result: Dict[str, Any]):
        """
        初始化PDG构建器
        
        Args:
            cfg: 控制流图
            dataflow_result: 数据流分析结果
        """
        self.cfg = cfg
        self.dataflow = dataflow_result
        self.pdg = nx.DiGraph()
        
        # 支配分析结果
        self.dominators: Dict[str, str] = {}
        self.dominator_tree: nx.DiGraph = nx.DiGraph()
        self.dominance_frontier: Dict[str, Set[str]] = defaultdict(set)
        self.post_dominators: Dict[str, str] = {}
        self.post_dominator_tree: nx.DiGraph = nx.DiGraph()
        
        # 依赖分析结果
        self.control_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.data_dependencies: Dict[str, Set[DependencyEdge]] = defaultdict(set)
        
        # 辅助数据结构
        self.entry_node: Optional[str] = None
        self.exit_nodes: Set[str] = set()
    
    def build_pdg(self) -> nx.DiGraph:
        """
        构建程序依赖图
        
        Returns:
            nx.DiGraph: 程序依赖图
        """
        logger.info("Building Program Dependence Graph...")
        
        try:
            # 1. 识别入口和出口节点
            self._identify_entry_exit_nodes()
            
            # 2. 构建支配树
            self._build_dominator_tree()
            
            # 3. 计算支配边界
            self._compute_dominance_frontier()
            
            # 4. 构建后支配树
            self._build_post_dominator_tree()
            
            # 5. 计算控制依赖
            self._compute_control_dependencies()
            
            # 6. 计算数据依赖
            self._compute_data_dependencies()
            
            # 7. 构建PDG
            self._build_pdg_graph()
            
            logger.info(f"PDG built with {self.pdg.number_of_nodes()} nodes and {self.pdg.number_of_edges()} edges")
            
            return self.pdg
            
        except Exception as e:
            logger.error(f"PDG construction failed at top level: {e}")
            # 返回一个简化的PDG，只包含CFG节点但没有依赖关系
            fallback_pdg = nx.DiGraph()
            for node in self.cfg.nodes:
                # 只复制基本信息，过滤不可序列化对象
                node_data = self.cfg.nodes[node]
                safe_data = {
                    'id': node,
                    'type': node_data.get('type', 'normal'),
                    'statements': node_data.get('statements', 0),
                    'variables': list(node_data.get('variables', []))
                }
                fallback_pdg.add_node(node, **safe_data)
            
            logger.warning("Returning simplified PDG without dependency analysis")
            return fallback_pdg
    
    def _identify_entry_exit_nodes(self):
        """识别入口和出口节点"""
        for node in self.cfg.nodes:
            node_data = self.cfg.nodes[node]
            if node_data.get('type') == 'entry':
                self.entry_node = node
            elif node_data.get('type') in ['exit', 'return']:
                self.exit_nodes.add(node)
        
        if not self.entry_node:
            # 如果没有明确的入口节点，选择第一个节点
            self.entry_node = list(self.cfg.nodes)[0] if self.cfg.nodes else None
        
        if not self.exit_nodes:
            # 如果没有明确的出口节点，选择没有后继的节点
            for node in self.cfg.nodes:
                if not list(self.cfg.successors(node)):
                    self.exit_nodes.add(node)
        
        logger.info(f"Entry node: {self.entry_node}, Exit nodes: {self.exit_nodes}")
    
    def _build_dominator_tree(self):
        """构建支配树 - 使用Lengauer-Tarjan算法的简化版本"""
        logger.info("Building dominator tree...")
        
        if not self.entry_node:
            logger.warning("No entry node found")
            return
        
        # 使用迭代算法计算支配关系
        # 初始化：每个节点的支配者集合包含所有节点
        dominators_sets = {}
        nodes = list(self.cfg.nodes)
        
        for node in nodes:
            if node == self.entry_node:
                dominators_sets[node] = {node}
            else:
                dominators_sets[node] = set(nodes)
        
        # 迭代计算支配者
        changed = True
        iterations = 0
        
        while changed and iterations < 100:
            changed = False
            iterations += 1
            
            for node in nodes:
                if node == self.entry_node:
                    continue
                
                # Dom(n) = {n} ∪ (∩ Dom(p) for all predecessors p of n)
                new_dominators = {node}
                
                predecessors = list(self.cfg.predecessors(node))
                if predecessors:
                    # 计算所有前驱的支配者集合的交集
                    intersection = dominators_sets[predecessors[0]].copy()
                    for pred in predecessors[1:]:
                        intersection.intersection_update(dominators_sets[pred])
                    new_dominators.update(intersection)
                
                if new_dominators != dominators_sets[node]:
                    dominators_sets[node] = new_dominators
                    changed = True
        
        # 构建直接支配关系
        for node in nodes:
            dominators = dominators_sets[node] - {node}
            if dominators:
                # 找到直接支配者（除了节点本身的最近支配者）
                immediate_dominator = None
                min_dom_count = float('inf')
                
                for dom in dominators:
                    dom_count = len(dominators_sets[dom])
                    if dom_count < min_dom_count:
                        min_dom_count = dom_count
                        immediate_dominator = dom
                
                if immediate_dominator:
                    self.dominators[node] = immediate_dominator
                    self.dominator_tree.add_edge(immediate_dominator, node)
        
        logger.info(f"Dominator tree built in {iterations} iterations")
    
    def _compute_dominance_frontier(self):
        """计算支配边界"""
        logger.info("Computing dominance frontier...")
        
        # 对于每个节点，计算其支配边界
        for node in self.cfg.nodes:
            # DF(n) = {y | ∃x.(x CFG-predecessor of y) ∧ (n dominates x) ∧ (n does not strictly dominate y)}
            for edge in self.cfg.edges():
                x, y = edge
                
                # 检查n是否支配x
                if self._dominates(node, x):
                    # 检查n是否严格支配y（n支配y且n≠y）
                    if not (self._dominates(node, y) and node != y):
                        self.dominance_frontier[node].add(y)
        
        logger.info("Dominance frontier computed")
    
    def _build_post_dominator_tree(self):
        """构建后支配树"""
        logger.info("Building post-dominator tree...")
        
        if not self.exit_nodes:
            logger.warning("No exit nodes found")
            return
        
        try:
            # 创建反向CFG
            reverse_cfg = self.cfg.reverse()
            
            # 添加虚拟出口节点连接所有真实出口节点
            virtual_exit = "virtual_exit"
            reverse_cfg.add_node(virtual_exit)
            for exit_node in self.exit_nodes:
                reverse_cfg.add_edge(virtual_exit, exit_node)
            
            # 在反向图上计算支配关系（即后支配关系）
            post_dominators_sets = {}
            nodes = list(reverse_cfg.nodes)
            
            for node in nodes:
                if node == virtual_exit:
                    post_dominators_sets[node] = {node}
                else:
                    post_dominators_sets[node] = set(nodes)
            
            # 迭代计算后支配者
            changed = True
            iterations = 0
            
            while changed and iterations < 100:
                changed = False
                iterations += 1
                
                for node in nodes:
                    if node == virtual_exit:
                        continue
                    
                    new_post_dominators = {node}
                    predecessors = list(reverse_cfg.predecessors(node))
                    
                    if predecessors:
                        intersection = post_dominators_sets[predecessors[0]].copy()
                        for pred in predecessors[1:]:
                            intersection.intersection_update(post_dominators_sets[pred])
                        new_post_dominators.update(intersection)
                    
                    if new_post_dominators != post_dominators_sets[node]:
                        post_dominators_sets[node] = new_post_dominators
                        changed = True
            
            # 构建直接后支配关系
            for node in nodes:
                if node == virtual_exit:
                    continue
                    
                post_dominators = post_dominators_sets[node] - {node}
                if post_dominators:
                    immediate_post_dominator = None
                    min_dom_count = float('inf')
                    
                    for dom in post_dominators:
                        if dom == virtual_exit:
                            continue
                        dom_count = len(post_dominators_sets[dom])
                        if dom_count < min_dom_count:
                            min_dom_count = dom_count
                            immediate_post_dominator = dom
                    
                    if immediate_post_dominator:
                        self.post_dominators[node] = immediate_post_dominator
                        self.post_dominator_tree.add_edge(immediate_post_dominator, node)
            
            logger.info(f"Post-dominator tree built in {iterations} iterations")
            
        except Exception as e:
            logger.warning(f"Post-dominator tree construction failed: {e}")
            logger.warning("Continuing without post-dominator analysis")
            # 不中断整个PDG构建过程
    
    def _compute_control_dependencies(self):
        """计算控制依赖"""
        logger.info("Computing control dependencies...")
        
        try:
            # 控制依赖定义：Y控制依赖于X当且仅当：
            # 1. 存在从X到Y的路径P
            # 2. X后支配P上的每个节点（除了Y）
            # 3. X不严格后支配Y
            
            for x in self.cfg.nodes:
                for y in self.cfg.nodes:
                    if x == y:
                        continue
                    
                    # 检查是否存在从x到y的路径
                    if nx.has_path(self.cfg, x, y):
                        # 检查后支配关系
                        if self._post_dominates(x, y):
                            continue  # x严格后支配y，不存在控制依赖
                        
                        # 查找x的所有后继
                        for succ in self.cfg.successors(x):
                            # 如果x后支配从succ到y路径上的所有节点（除了y）
                            if self._controls_path_to(x, succ, y):
                                self.control_dependencies[y].add(x)
                                break
            
            logger.info(f"Control dependencies computed for {len(self.control_dependencies)} nodes")
            
        except Exception as e:
            logger.warning(f"Control dependencies computation failed: {e}")
            logger.warning("Continuing without control dependencies")
    
    def _compute_data_dependencies(self):
        """计算数据依赖"""
        logger.info("Computing data dependencies...")
        
        # 数据依赖基于到达定值分析的结果
        reaching_defs = self.dataflow.get('reaching_definitions', {})
        reaching_defs_in = reaching_defs.get('in', {})
        
        for node in self.cfg.nodes:
            node_data = self.cfg.nodes[node]
            used_variables = self._get_used_variables(node_data)
            
            for var in used_variables:
                # 查找到达该使用点的所有定义
                reaching_definitions = reaching_defs_in.get(node, set())
                
                for definition in reaching_definitions:
                    if hasattr(definition, 'variable') and definition.variable == var:
                        # 创建数据依赖边
                        dep_edge = DependencyEdge(
                            source=definition.block_id,
                            target=node,
                            dep_type='data',
                            variable=var
                        )
                        self.data_dependencies[node].add(dep_edge)
        
        logger.info(f"Data dependencies computed for {len(self.data_dependencies)} nodes")
    
    def _build_pdg_graph(self):
        """构建PDG图"""
        logger.info("Building PDG graph...")
        
        # 添加所有CFG节点到PDG
        for node in self.cfg.nodes:
            node_data = self.cfg.nodes[node].copy()
            # 过滤掉不可序列化的clang对象
            filtered_data = self._filter_serializable_data(node_data)
            self.pdg.add_node(node, **filtered_data)
        
        # 添加控制依赖边
        for target, sources in self.control_dependencies.items():
            for source in sources:
                self.pdg.add_edge(
                    source, target, 
                    type='control',
                    label='control'
                )
        
        # 添加数据依赖边
        for target, dep_edges in self.data_dependencies.items():
            for dep_edge in dep_edges:
                self.pdg.add_edge(
                    dep_edge.source, dep_edge.target,
                    type='data',
                    variable=dep_edge.variable,
                    label=f'data:{dep_edge.variable}'
                )
        
        logger.info("PDG graph construction completed")
    
    def _filter_serializable_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤掉不可序列化的数据（如clang对象）"""
        filtered = {}
        
        for key, value in data.items():
            try:
                # 尝试序列化测试
                import pickle
                pickle.dumps(value)
                filtered[key] = value
            except (TypeError, AttributeError) as e:
                # 跳过不可序列化的对象（如clang cursors）
                if "ctypes" in str(e) or "pickle" in str(e):
                    logger.debug(f"Skipping unpicklable attribute '{key}': {type(value)}")
                    # 对于clang对象，尝试提取基本信息
                    if hasattr(value, 'spelling'):
                        filtered[f"{key}_name"] = value.spelling
                    elif hasattr(value, 'location') and hasattr(value.location, 'line'):
                        filtered[f"{key}_location"] = f"line {value.location.line}"
                else:
                    # 其他错误，记录但不中断
                    logger.warning(f"Could not serialize attribute '{key}': {e}")
        
        return filtered
    
    def _dominates(self, dominator: str, node: str) -> bool:
        """检查dominator是否支配node"""
        if dominator == node:
            return True
        
        current = node
        while current in self.dominators:
            current = self.dominators[current]
            if current == dominator:
                return True
        
        return False
    
    def _post_dominates(self, post_dominator: str, node: str) -> bool:
        """检查post_dominator是否后支配node"""
        if post_dominator == node:
            return True
        
        current = node
        while current in self.post_dominators:
            current = self.post_dominators[current]
            if current == post_dominator:
                return True
        
        return False
    
    def _controls_path_to(self, control_node: str, start: str, target: str) -> bool:
        """检查control_node是否控制从start到target的路径"""
        # 简化实现：检查是否存在路径且control_node后支配路径上的节点
        try:
            if not nx.has_path(self.cfg, start, target):
                return False
            
            # 获取从start到target的所有简单路径
            paths = list(nx.all_simple_paths(self.cfg, start, target))
            
            for path in paths:
                # 检查control_node是否后支配路径上的所有节点（除了target）
                for node in path[:-1]:  # 不包括target
                    if not self._post_dominates(control_node, node):
                        return False
            
            return True
            
        except nx.NetworkXNoPath:
            return False
    
    def _get_used_variables(self, node_data: Dict[str, Any]) -> Set[str]:
        """从节点数据中获取使用的变量"""
        variables = node_data.get('variables', [])
        # 简化实现：假设所有变量都被使用
        return set(variables)
    
    def get_control_dependencies(self, node: str) -> Set[str]:
        """获取节点的控制依赖"""
        return self.control_dependencies.get(node, set()).copy()
    
    def get_data_dependencies(self, node: str) -> Set[DependencyEdge]:
        """获取节点的数据依赖"""
        return self.data_dependencies.get(node, set()).copy()
    
    def get_dependent_nodes(self, node: str) -> Dict[str, Set[str]]:
        """获取依赖于指定节点的所有节点"""
        control_dependents = set()
        data_dependents = set()
        
        # 查找控制依赖
        for target, sources in self.control_dependencies.items():
            if node in sources:
                control_dependents.add(target)
        
        # 查找数据依赖
        for target, dep_edges in self.data_dependencies.items():
            for dep_edge in dep_edges:
                if dep_edge.source == node:
                    data_dependents.add(target)
        
        return {
            'control': control_dependents,
            'data': data_dependents
        }
    
    def slice_program(self, slicing_criterion: Tuple[str, str]) -> Set[str]:
        """程序切片 - 计算影响切片准则的所有语句"""
        node, variable = slicing_criterion
        
        # 后向切片：找到所有影响切片准则的语句
        slice_nodes = set()
        worklist = deque([(node, variable)])
        visited = set()
        
        while worklist:
            current_node, current_var = worklist.popleft()
            
            if (current_node, current_var) in visited:
                continue
            visited.add((current_node, current_var))
            
            slice_nodes.add(current_node)
            
            # 添加控制依赖
            for control_dep in self.get_control_dependencies(current_node):
                worklist.append((control_dep, current_var))
            
            # 添加数据依赖
            for dep_edge in self.get_data_dependencies(current_node):
                if dep_edge.variable == current_var:
                    worklist.append((dep_edge.source, current_var))
        
        return slice_nodes
    
    def find_equivalent_nodes(self) -> List[Set[str]]:
        """查找等价节点（具有相同依赖关系的节点）"""
        equivalence_classes = []
        processed = set()
        
        for node1 in self.pdg.nodes:
            if node1 in processed:
                continue
            
            equivalent_nodes = {node1}
            
            # 获取node1的依赖关系
            deps1 = self._get_node_dependencies(node1)
            
            for node2 in self.pdg.nodes:
                if node2 != node1 and node2 not in processed:
                    deps2 = self._get_node_dependencies(node2)
                    
                    # 比较依赖关系
                    if deps1 == deps2:
                        equivalent_nodes.add(node2)
            
            if len(equivalent_nodes) > 1:
                equivalence_classes.append(equivalent_nodes)
            
            processed.update(equivalent_nodes)
        
        return equivalence_classes
    
    def _get_node_dependencies(self, node: str) -> Tuple[Set[str], Set[Tuple[str, str]]]:
        """获取节点的所有依赖关系"""
        control_deps = self.get_control_dependencies(node)
        data_deps = set()
        
        for dep_edge in self.get_data_dependencies(node):
            data_deps.add((dep_edge.source, dep_edge.variable or ''))
        
        return (control_deps, data_deps)
    
    def analyze_dependencies(self) -> Dict[str, Any]:
        """分析依赖关系统计"""
        stats = {
            'total_nodes': self.pdg.number_of_nodes(),
            'total_edges': self.pdg.number_of_edges(),
            'control_edges': 0,
            'data_edges': 0,
            'nodes_with_control_deps': 0,
            'nodes_with_data_deps': 0,
            'max_control_deps': 0,
            'max_data_deps': 0
        }
        
        for edge_data in self.pdg.edges(data=True):
            if edge_data[2].get('type') == 'control':
                stats['control_edges'] += 1
            elif edge_data[2].get('type') == 'data':
                stats['data_edges'] += 1
        
        for node in self.pdg.nodes:
            control_deps = len(self.get_control_dependencies(node))
            data_deps = len(self.get_data_dependencies(node))
            
            if control_deps > 0:
                stats['nodes_with_control_deps'] += 1
                stats['max_control_deps'] = max(stats['max_control_deps'], control_deps)
            
            if data_deps > 0:
                stats['nodes_with_data_deps'] += 1
                stats['max_data_deps'] = max(stats['max_data_deps'], data_deps)
        
        return stats
    
    def print_pdg_summary(self):
        """打印PDG摘要信息"""
        stats = self.analyze_dependencies()
        
        print("=== Program Dependence Graph Summary ===")
        print(f"Total nodes: {stats['total_nodes']}")
        print(f"Total edges: {stats['total_edges']}")
        print(f"Control edges: {stats['control_edges']}")
        print(f"Data edges: {stats['data_edges']}")
        print(f"Nodes with control dependencies: {stats['nodes_with_control_deps']}")
        print(f"Nodes with data dependencies: {stats['nodes_with_data_deps']}")
        print(f"Maximum control dependencies per node: {stats['max_control_deps']}")
        print(f"Maximum data dependencies per node: {stats['max_data_deps']}")
        
        print(f"\nDominator tree nodes: {self.dominator_tree.number_of_nodes()}")
        print(f"Post-dominator tree nodes: {self.post_dominator_tree.number_of_nodes()}")
        
        # 打印一些示例依赖关系
        print(f"\nSample control dependencies:")
        count = 0
        for target, sources in self.control_dependencies.items():
            if sources and count < 5:
                print(f"  {target} <- {list(sources)[:3]}")
                count += 1
        
        print(f"\nSample data dependencies:")
        count = 0
        for target, dep_edges in self.data_dependencies.items():
            if dep_edges and count < 5:
                sample_edges = list(dep_edges)[:3]
                edge_strs = [f"{e.source}({e.variable})" for e in sample_edges]
                print(f"  {target} <- {edge_strs}")
                count += 1