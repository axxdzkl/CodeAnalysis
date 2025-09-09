"""
函数间分析模块

本模块实现了函数间数据依赖分析，包括：
- 函数摘要构建
- 参数传递分析
- 全局变量访问分析
- 函数间依赖传播
"""

import networkx as nx
from typing import Dict, Set, List, Any, Optional
import logging
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class FunctionSummary:
    """函数摘要信息"""
    name: str
    inputs: Set[str]  # 输入参数和全局变量
    outputs: Set[str]  # 输出参数和全局变量
    globals_read: Set[str]  # 读取的全局变量
    globals_write: Set[str]  # 写入的全局变量
    side_effects: bool  # 是否有副作用

class InterproceduralAnalyzer:
    """函数间分析器"""
    
    def __init__(self, call_graph: nx.DiGraph, pdgs: Dict[str, nx.DiGraph]):
        self.call_graph = call_graph
        self.pdgs = pdgs  # 函数名到PDG的映射
        self.summaries: Dict[str, FunctionSummary] = {}
        self.interprocedural_pdg = nx.DiGraph()
        
        # 全局变量信息
        self.global_variables: Set[str] = set()
        self.function_params: Dict[str, List[str]] = {}
    
    def analyze(self) -> Dict[str, Any]:
        """执行函数间分析"""
        logger.info("Starting interprocedural analysis...")
        
        # 1. 收集全局变量和函数参数
        self._collect_global_info()
        
        # 2. 构建函数摘要
        self._build_function_summaries()
        
        # 3. 传播函数间依赖
        self._propagate_interprocedural_dependencies()
        
        # 4. 构建函数间PDG
        self._build_interprocedural_pdg()
        
        logger.info("Interprocedural analysis completed")
        
        return {
            'summaries': self.summaries,
            'interprocedural_pdg': self.interprocedural_pdg,
            'global_variables': self.global_variables
        }
    
    def _collect_global_info(self):
        """收集全局变量和函数参数信息"""
        logger.info("Collecting global information...")
        
        # 从调用图中提取函数参数信息
        for func_name in self.call_graph.nodes:
            func_info = self.call_graph.nodes[func_name].get('function_info')
            if func_info:
                params = [param[0] for param in func_info.parameters]
                self.function_params[func_name] = params
        
        # 从PDG中识别全局变量（简化实现）
        for func_name, pdg in self.pdgs.items():
            for node in pdg.nodes:
                variables = pdg.nodes[node].get('variables', [])
                for var in variables:
                    # 简化启发式：大写开头或带下划线的可能是全局变量
                    if var.isupper() or var.startswith('g_') or var.startswith('_'):
                        self.global_variables.add(var)
    
    def _build_function_summaries(self):
        """构建函数摘要"""
        logger.info("Building function summaries...")
        
        for func_name in self.call_graph.nodes:
            pdg = self.pdgs.get(func_name)
            if not pdg:
                # 为没有PDG的函数创建空摘要
                summary = FunctionSummary(
                    name=func_name,
                    inputs=set(),
                    outputs=set(),
                    globals_read=set(),
                    globals_write=set(),
                    side_effects=False
                )
                self.summaries[func_name] = summary
                continue
            
            # 分析函数的输入输出
            inputs = self._analyze_function_inputs(func_name, pdg)
            outputs = self._analyze_function_outputs(func_name, pdg)
            globals_access = self._analyze_global_access(func_name, pdg)
            side_effects = self._has_side_effects(func_name, pdg)
            
            summary = FunctionSummary(
                name=func_name,
                inputs=inputs,
                outputs=outputs,
                globals_read=globals_access['read'],
                globals_write=globals_access['write'],
                side_effects=side_effects
            )
            
            self.summaries[func_name] = summary
        
        logger.info(f"Built summaries for {len(self.summaries)} functions")
    
    def _analyze_function_inputs(self, func_name: str, pdg: nx.DiGraph) -> Set[str]:
        """分析函数输入"""
        inputs = set()
        
        # 添加函数参数
        params = self.function_params.get(func_name, [])
        inputs.update(params)
        
        # 查找入口节点使用的变量
        entry_nodes = [n for n in pdg.nodes if pdg.nodes[n].get('type') == 'entry']
        
        for entry_node in entry_nodes:
            variables = pdg.nodes[entry_node].get('variables', [])
            for var in variables:
                if var in self.global_variables:
                    inputs.add(var)
        
        return inputs
    
    def _analyze_function_outputs(self, func_name: str, pdg: nx.DiGraph) -> Set[str]:
        """分析函数输出"""
        outputs = set()
        
        # 查找出口节点定义的变量
        exit_nodes = [n for n in pdg.nodes if pdg.nodes[n].get('type') in ['exit', 'return']]
        
        for exit_node in exit_nodes:
            variables = pdg.nodes[exit_node].get('variables', [])
            for var in variables:
                if var in self.global_variables:
                    outputs.add(var)
        
        # 分析返回值（简化处理）
        func_info = self.call_graph.nodes[func_name].get('function_info')
        if func_info and func_info.return_type != 'void':
            outputs.add('__return_value__')
        
        return outputs
    
    def _analyze_global_access(self, func_name: str, pdg: nx.DiGraph) -> Dict[str, Set[str]]:
        """分析全局变量访问"""
        globals_access = {'read': set(), 'write': set()}
        
        for node in pdg.nodes:
            variables = pdg.nodes[node].get('variables', [])
            for var in variables:
                if var in self.global_variables:
                    # 简化处理：假设所有全局变量都被读写
                    globals_access['read'].add(var)
                    globals_access['write'].add(var)
        
        return globals_access
    
    def _has_side_effects(self, func_name: str, pdg: nx.DiGraph) -> bool:
        """检查函数是否有副作用"""
        # 简化实现：如果修改全局变量或调用其他函数则有副作用
        summary = self.summaries.get(func_name)
        if summary and summary.globals_write:
            return True
        
        # 检查是否调用其他函数
        callees = set(self.call_graph.successors(func_name))
        return len(callees) > 0
    
    def _propagate_interprocedural_dependencies(self):
        """传播函数间依赖"""
        logger.info("Propagating interprocedural dependencies...")
        
        # 按调用拓扑顺序处理函数
        try:
            topo_order = list(nx.topological_sort(self.call_graph))
        except nx.NetworkXError:
            # 如果有循环，使用强连通分量
            topo_order = []
            for component in nx.strongly_connected_components(self.call_graph):
                topo_order.extend(component)
        
        for func in topo_order:
            callers = list(self.call_graph.predecessors(func))
            
            for caller in callers:
                self._propagate_from_callee(caller, func)
    
    def _propagate_from_callee(self, caller: str, callee: str):
        """从被调用函数传播依赖到调用者"""
        caller_summary = self.summaries.get(caller)
        callee_summary = self.summaries.get(callee)
        
        if not caller_summary or not callee_summary:
            return
        
        # 传播输入依赖
        caller_summary.inputs.update(callee_summary.inputs)
        
        # 传播全局变量访问
        caller_summary.globals_read.update(callee_summary.globals_read)
        caller_summary.globals_write.update(callee_summary.globals_write)
        
        # 传播副作用
        if callee_summary.side_effects:
            caller_summary.side_effects = True
    
    def _build_interprocedural_pdg(self):
        """构建函数间PDG"""
        logger.info("Building interprocedural PDG...")
        
        # 添加所有函数节点
        for func_name in self.call_graph.nodes:
            self.interprocedural_pdg.add_node(func_name, summary=self.summaries.get(func_name))
        
        # 添加函数间数据依赖边
        for func_name in self.call_graph.nodes:
            summary = self.summaries.get(func_name)
            if not summary:
                continue
            
            # 查找依赖此函数输出的函数
            for other_func in self.call_graph.nodes:
                if other_func == func_name:
                    continue
                
                other_summary = self.summaries.get(other_func)
                if not other_summary:
                    continue
                
                # 检查数据依赖
                common_globals = summary.globals_write & other_summary.globals_read
                if common_globals:
                    self.interprocedural_pdg.add_edge(
                        func_name, other_func,
                        type='interprocedural_data',
                        variables=list(common_globals)
                    )
        
        # 添加调用依赖边
        for edge in self.call_graph.edges():
            caller, callee = edge
            self.interprocedural_pdg.add_edge(
                caller, callee,
                type='call',
                call_info=self.call_graph.edges[edge].get('call_info')
            )
    
    def get_function_dependencies(self, func_name: str) -> Dict[str, Set[str]]:
        """获取函数的依赖关系"""
        dependencies = {
            'data_dependencies': set(),
            'call_dependencies': set(),
            'global_dependencies': set()
        }
        
        summary = self.summaries.get(func_name)
        if not summary:
            return dependencies
        
        # 数据依赖：依赖于修改相同全局变量的函数
        for other_func, other_summary in self.summaries.items():
            if other_func == func_name:
                continue
            
            # 检查全局变量依赖
            common_vars = summary.globals_read & other_summary.globals_write
            if common_vars:
                dependencies['data_dependencies'].add(other_func)
                dependencies['global_dependencies'].update(common_vars)
        
        # 调用依赖
        dependencies['call_dependencies'].update(self.call_graph.successors(func_name))
        
        return dependencies
    
    def compute_coupling_metrics(self) -> Dict[str, Dict[str, Any]]:
        """计算函数间耦合度指标"""
        coupling_metrics = {}
        
        for func_name in self.call_graph.nodes:
            summary = self.summaries.get(func_name)
            if not summary:
                continue
            
            # 计算各种耦合度指标
            data_coupling = len(summary.globals_read) + len(summary.globals_write)
            
            # 参数耦合
            param_coupling = len(summary.inputs)
            
            # 调用耦合
            call_coupling = self.call_graph.out_degree(func_name) + self.call_graph.in_degree(func_name)
            
            # 副作用耦合
            side_effect_coupling = 1 if summary.side_effects else 0
            
            # 总耦合度
            total_coupling = data_coupling + param_coupling + call_coupling + side_effect_coupling
            
            coupling_metrics[func_name] = {
                'data_coupling': data_coupling,
                'parameter_coupling': param_coupling,
                'call_coupling': call_coupling,
                'side_effect_coupling': side_effect_coupling,
                'total_coupling': total_coupling
            }
        
        return coupling_metrics
    
    def find_tightly_coupled_functions(self, threshold: int = 5) -> List[Set[str]]:
        """查找紧耦合的函数组"""
        coupling_metrics = self.compute_coupling_metrics()
        tightly_coupled = []
        
        # 基于共享全局变量的耦合分析
        global_var_usage = defaultdict(set)
        
        for func_name, summary in self.summaries.items():
            for var in summary.globals_read | summary.globals_write:
                global_var_usage[var].add(func_name)
        
        # 找到共享多个全局变量的函数组
        processed = set()
        for var, funcs in global_var_usage.items():
            if len(funcs) > 1:
                func_set = frozenset(funcs)
                if func_set not in processed:
                    processed.add(func_set)
                    
                    # 计算组内平均耦合度
                    total_coupling = sum(coupling_metrics.get(f, {}).get('total_coupling', 0) for f in funcs)
                    avg_coupling = total_coupling / len(funcs)
                    
                    if avg_coupling >= threshold:
                        tightly_coupled.append(funcs)
        
        return tightly_coupled
    
    def analyze_change_impact(self, changed_function: str) -> Set[str]:
        """分析函数变更的影响范围"""
        impacted = set()
        
        if changed_function not in self.summaries:
            return impacted
        
        # 直接影响：调用此函数的函数
        impacted.update(self.call_graph.predecessors(changed_function))
        
        # 间接影响：通过全局变量影响的函数
        changed_summary = self.summaries[changed_function]
        
        for func_name, summary in self.summaries.items():
            if func_name == changed_function:
                continue
            
            # 如果其他函数读取了此函数修改的全局变量
            if summary.globals_read & changed_summary.globals_write:
                impacted.add(func_name)
        
        return impacted
    
    def print_interprocedural_summary(self):
        """打印函数间分析摘要"""
        coupling_metrics = self.compute_coupling_metrics()
        
        print("=== Interprocedural Analysis Summary ===")
        print(f"Total functions analyzed: {len(self.summaries)}")
        print(f"Global variables found: {len(self.global_variables)}")
        
        # 统计副作用函数
        side_effect_funcs = sum(1 for s in self.summaries.values() if s.side_effects)
        print(f"Functions with side effects: {side_effect_funcs}")
        
        # 耦合度统计
        if coupling_metrics:
            total_couplings = [m['total_coupling'] for m in coupling_metrics.values()]
            avg_coupling = sum(total_couplings) / len(total_couplings)
            max_coupling = max(total_couplings)
            
            print(f"Average coupling per function: {avg_coupling:.2f}")
            print(f"Maximum coupling: {max_coupling}")
            
            # 最高耦合度的函数
            max_coupled_func = max(coupling_metrics.items(), key=lambda x: x[1]['total_coupling'])
            print(f"Most coupled function: {max_coupled_func[0]} (coupling: {max_coupled_func[1]['total_coupling']})")
        
        # 紧耦合函数组
        tightly_coupled = self.find_tightly_coupled_functions()
        if tightly_coupled:
            print(f"Tightly coupled function groups: {len(tightly_coupled)}")
            for i, group in enumerate(tightly_coupled[:3]):  # 显示前3组
                print(f"  Group {i+1}: {list(group)}")
        
        print(f"Interprocedural PDG edges: {self.interprocedural_pdg.number_of_edges()}")


class GlobalVariableAnalyzer:
    """全局变量分析器"""
    
    def __init__(self, summaries: Dict[str, FunctionSummary]):
        self.summaries = summaries
        self.global_var_graph = nx.DiGraph()
    
    def analyze_global_dependencies(self) -> Dict[str, Any]:
        """分析全局变量依赖关系"""
        # 构建全局变量依赖图
        for func_name, summary in self.summaries.items():
            self.global_var_graph.add_node(func_name)
            
            # 为每个全局变量创建节点
            for var in summary.globals_read | summary.globals_write:
                var_node = f"global_{var}"
                self.global_var_graph.add_node(var_node, type='global_variable')
                
                if var in summary.globals_read:
                    self.global_var_graph.add_edge(var_node, func_name, type='read')
                
                if var in summary.globals_write:
                    self.global_var_graph.add_edge(func_name, var_node, type='write')
        
        return {
            'global_var_graph': self.global_var_graph,
            'variable_usage': self._compute_variable_usage()
        }
    
    def _compute_variable_usage(self) -> Dict[str, Dict[str, int]]:
        """计算变量使用统计"""
        usage_stats = {}
        
        # 收集所有全局变量
        global_vars = set()
        for summary in self.summaries.values():
            global_vars.update(summary.globals_read)
            global_vars.update(summary.globals_write)
        
        for var in global_vars:
            readers = sum(1 for s in self.summaries.values() if var in s.globals_read)
            writers = sum(1 for s in self.summaries.values() if var in s.globals_write)
            
            usage_stats[var] = {
                'readers': readers,
                'writers': writers,
                'total_usage': readers + writers
            }
        
        return usage_stats