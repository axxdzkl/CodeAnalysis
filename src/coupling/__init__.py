"""
耦合度计算模块

本模块实现了多种耦合度指标的计算，包括：
- 数据耦合(Data Coupling)
- 控制耦合(Control Coupling)  
- 参数耦合(Parameter Coupling)
- 全局耦合(Global Coupling)
- 内容耦合(Content Coupling)
"""

import networkx as nx
from typing import Dict, Set, List, Any, Tuple, Optional
import logging
from dataclasses import dataclass
from collections import defaultdict
import math

logger = logging.getLogger(__name__)

@dataclass
class CouplingMetrics:
    """耦合度指标"""
    afferent: int  # 入耦合(被其他模块依赖)
    efferent: int  # 出耦合(依赖其他模块)
    instability: float  # 不稳定度 I = Ce / (Ca + Ce)
    abstractness: float  # 抽象度
    distance: float  # 距离主序列的距离
    data_coupling: int  # 数据耦合
    control_coupling: int  # 控制耦合
    parameter_coupling: int  # 参数耦合
    global_coupling: int  # 全局耦合

class CouplingCalculator:
    """耦合度计算器"""
    
    def __init__(self, call_graph: nx.DiGraph, interprocedural_result: Dict[str, Any]):
        self.call_graph = call_graph
        self.interprocedural_result = interprocedural_result
        self.summaries = interprocedural_result.get('summaries', {})
        self.global_variables = interprocedural_result.get('global_variables', set())
        
        # 计算结果存储
        self.coupling_metrics: Dict[str, CouplingMetrics] = {}
        self.coupling_matrix: Dict[Tuple[str, str], float] = {}
        
        # 统计信息
        self.stats = {
            'total_functions': 0,
            'avg_coupling': 0.0,
            'max_coupling': 0.0,
            'coupling_distribution': defaultdict(int)
        }
    
    def calculate_coupling(self) -> Dict[str, Any]:
        """计算所有耦合度指标"""
        logger.info("Calculating coupling metrics...")
        
        # 1. 计算基本耦合指标
        self._calculate_basic_coupling()
        
        # 2. 计算数据耦合
        self._calculate_data_coupling()
        
        # 3. 计算控制耦合
        self._calculate_control_coupling()
        
        # 4. 计算参数耦合
        self._calculate_parameter_coupling()
        
        # 5. 计算全局耦合
        self._calculate_global_coupling()
        
        # 6. 计算高级指标
        self._calculate_advanced_metrics()
        
        # 7. 构建耦合矩阵
        self._build_coupling_matrix()
        
        # 8. 计算统计信息
        self._calculate_statistics()
        
        logger.info("Coupling calculation completed")
        
        return {
            'metrics': self.coupling_metrics,
            'matrix': self.coupling_matrix,
            'statistics': self.stats
        }
    
    def _calculate_basic_coupling(self):
        """计算基本耦合指标"""
        logger.info("Calculating basic coupling metrics...")
        
        for func in self.call_graph.nodes:
            # 计算入耦合和出耦合
            afferent = self.call_graph.in_degree(func)  # 有多少函数调用此函数
            efferent = self.call_graph.out_degree(func)  # 此函数调用多少个其他函数
            
            # 计算不稳定度
            instability = efferent / (afferent + efferent) if (afferent + efferent) > 0 else 0
            
            # 初始化指标对象
            metrics = CouplingMetrics(
                afferent=afferent,
                efferent=efferent,
                instability=instability,
                abstractness=0.0,  # 后续计算
                distance=0.0,     # 后续计算
                data_coupling=0,
                control_coupling=0,
                parameter_coupling=0,
                global_coupling=0
            )
            
            self.coupling_metrics[func] = metrics
    
    def _calculate_data_coupling(self):
        """计算数据耦合度"""
        logger.info("Calculating data coupling...")
        
        for func, metrics in self.coupling_metrics.items():
            data_coupling = 0
            summary = self.summaries.get(func)
            
            if summary:
                # 参数传递的数据量
                data_coupling += len(summary.inputs)
                data_coupling += len(summary.outputs)
                
                # 通过全局变量共享的数据
                data_coupling += len(summary.globals_read)
                data_coupling += len(summary.globals_write)
            
            metrics.data_coupling = data_coupling
    
    def _calculate_control_coupling(self):
        """计算控制耦合度"""
        logger.info("Calculating control coupling...")
        
        for func, metrics in self.coupling_metrics.items():
            control_coupling = 0
            
            # 检查函数指针调用
            for edge_data in self.call_graph.edges(data=True):
                caller, callee, data = edge_data
                if caller == func:
                    call_info = data.get('call_info')
                    if call_info and call_info.call_type in ['indirect', 'function_pointer']:
                        control_coupling += 1
            
            # 检查控制标志传递
            summary = self.summaries.get(func)
            if summary:
                for input_var in summary.inputs:
                    if self._is_control_flag(input_var):
                        control_coupling += 1
            
            metrics.control_coupling = control_coupling
    
    def _calculate_parameter_coupling(self):
        """计算参数耦合度"""
        logger.info("Calculating parameter coupling...")
        
        for func, metrics in self.coupling_metrics.items():
            parameter_coupling = 0
            
            # 获取函数信息
            func_info = self.call_graph.nodes[func].get('function_info')
            if func_info:
                # 参数数量贡献耦合度
                parameter_coupling += len(func_info.parameters)
                
                # 复杂参数类型增加耦合度
                for param_name, param_type in func_info.parameters:
                    if self._is_complex_type(param_type):
                        parameter_coupling += 1
            
            metrics.parameter_coupling = parameter_coupling
    
    def _calculate_global_coupling(self):
        """计算全局耦合度"""
        logger.info("Calculating global coupling...")
        
        for func, metrics in self.coupling_metrics.items():
            global_coupling = 0
            summary = self.summaries.get(func)
            
            if summary:
                # 全局变量访问数量
                global_coupling += len(summary.globals_read)
                global_coupling += len(summary.globals_write)
                
                # 检查与其他函数的全局变量共享
                for other_func, other_summary in self.summaries.items():
                    if func != other_func:
                        shared_reads = summary.globals_read & other_summary.globals_read
                        shared_writes = summary.globals_write & other_summary.globals_write
                        cross_access = (summary.globals_read & other_summary.globals_write) | \
                                     (summary.globals_write & other_summary.globals_read)
                        
                        global_coupling += len(shared_reads) + len(shared_writes) + len(cross_access)
            
            metrics.global_coupling = global_coupling
    
    def _calculate_advanced_metrics(self):
        """计算高级耦合指标"""
        logger.info("Calculating advanced metrics...")
        
        for func, metrics in self.coupling_metrics.items():
            # 计算抽象度（简化实现：基于是否是叶子函数）
            metrics.abstractness = 1.0 if metrics.efferent == 0 else 0.0
            
            # 计算距离主序列的距离
            # 主序列：A + I = 1（理想情况）
            metrics.distance = abs(metrics.abstractness + metrics.instability - 1.0)
    
    def _build_coupling_matrix(self):
        """构建函数间耦合矩阵"""
        logger.info("Building coupling matrix...")
        
        functions = list(self.call_graph.nodes)
        
        for i, func1 in enumerate(functions):
            for j, func2 in enumerate(functions):
                if i != j:
                    coupling = self._calculate_pairwise_coupling(func1, func2)
                    self.coupling_matrix[(func1, func2)] = coupling
    
    def _calculate_pairwise_coupling(self, func1: str, func2: str) -> float:
        """计算两个函数之间的耦合度"""
        coupling = 0.0
        
        # 直接调用关系
        if self.call_graph.has_edge(func1, func2):
            coupling += 1.0
        
        # 共享全局变量
        summary1 = self.summaries.get(func1)
        summary2 = self.summaries.get(func2)
        
        if summary1 and summary2:
            # 数据耦合：共享变量
            shared_vars = (summary1.globals_read & summary2.globals_read) | \
                         (summary1.globals_write & summary2.globals_write) | \
                         (summary1.globals_read & summary2.globals_write) | \
                         (summary1.globals_write & summary2.globals_read)
            
            coupling += len(shared_vars) * 0.5
            
            # 参数传递耦合
            if self.call_graph.has_edge(func1, func2):
                # 获取调用时的参数传递信息
                edge_data = self.call_graph.edges[func1, func2]
                call_info = edge_data.get('call_info')
                if call_info:
                    coupling += len(call_info.arguments) * 0.2
        
        return coupling
    
    def _calculate_statistics(self):
        """计算统计信息"""
        if not self.coupling_metrics:
            return
        
        self.stats['total_functions'] = len(self.coupling_metrics)
        
        # 计算平均耦合度
        total_coupling = sum(
            m.data_coupling + m.control_coupling + m.parameter_coupling + m.global_coupling
            for m in self.coupling_metrics.values()
        )
        self.stats['avg_coupling'] = total_coupling / len(self.coupling_metrics)
        
        # 计算最大耦合度
        max_coupling = max(
            m.data_coupling + m.control_coupling + m.parameter_coupling + m.global_coupling
            for m in self.coupling_metrics.values()
        )
        self.stats['max_coupling'] = max_coupling
        
        # 耦合度分布
        for metrics in self.coupling_metrics.values():
            total = metrics.data_coupling + metrics.control_coupling + \
                   metrics.parameter_coupling + metrics.global_coupling
            
            if total == 0:
                self.stats['coupling_distribution']['none'] += 1
            elif total <= 5:
                self.stats['coupling_distribution']['low'] += 1
            elif total <= 15:
                self.stats['coupling_distribution']['medium'] += 1
            else:
                self.stats['coupling_distribution']['high'] += 1
    
    def _is_control_flag(self, var_name: str) -> bool:
        """判断变量是否是控制标志"""
        control_keywords = ['flag', 'switch', 'control', 'mode', 'status', 'state']
        return any(keyword in var_name.lower() for keyword in control_keywords)
    
    def _is_complex_type(self, type_str: str) -> bool:
        """判断是否是复杂类型"""
        complex_indicators = ['struct', 'union', 'enum', '*', '[', 'const']
        return any(indicator in type_str for indicator in complex_indicators)
    
    def get_function_coupling(self, func_name: str) -> Optional[CouplingMetrics]:
        """获取指定函数的耦合度指标"""
        return self.coupling_metrics.get(func_name)
    
    def get_most_coupled_functions(self, n: int = 10) -> List[Tuple[str, float]]:
        """获取耦合度最高的N个函数"""
        coupled_functions = []
        
        for func, metrics in self.coupling_metrics.items():
            total_coupling = metrics.data_coupling + metrics.control_coupling + \
                           metrics.parameter_coupling + metrics.global_coupling
            coupled_functions.append((func, total_coupling))
        
        coupled_functions.sort(key=lambda x: x[1], reverse=True)
        return coupled_functions[:n]
    
    def get_unstable_functions(self, threshold: float = 0.8) -> List[str]:
        """获取不稳定度高的函数"""
        unstable = []
        
        for func, metrics in self.coupling_metrics.items():
            if metrics.instability >= threshold:
                unstable.append(func)
        
        return unstable
    
    def analyze_coupling_hotspots(self) -> Dict[str, Any]:
        """分析耦合热点"""
        hotspots = {
            'high_coupling_functions': self.get_most_coupled_functions(5),
            'unstable_functions': self.get_unstable_functions(),
            'coupling_clusters': self._find_coupling_clusters(),
            'global_variable_hotspots': self._find_global_variable_hotspots()
        }
        
        return hotspots
    
    def _find_coupling_clusters(self) -> List[Set[str]]:
        """查找高耦合的函数集群"""
        clusters = []
        threshold = self.stats['avg_coupling'] * 1.5  # 高于平均值50%
        
        # 创建高耦合函数的子图
        high_coupling_funcs = set()
        for func, metrics in self.coupling_metrics.items():
            total_coupling = metrics.data_coupling + metrics.control_coupling + \
                           metrics.parameter_coupling + metrics.global_coupling
            if total_coupling >= threshold:
                high_coupling_funcs.add(func)
        
        if len(high_coupling_funcs) <= 1:
            return clusters
        
        # 在高耦合函数中查找连通分量
        subgraph = self.call_graph.subgraph(high_coupling_funcs)
        components = nx.weakly_connected_components(subgraph)
        
        for component in components:
            if len(component) > 1:
                clusters.append(component)
        
        return clusters
    
    def _find_global_variable_hotspots(self) -> List[Tuple[str, int]]:
        """查找全局变量热点"""
        var_usage = defaultdict(int)
        
        for summary in self.summaries.values():
            for var in summary.globals_read | summary.globals_write:
                var_usage[var] += 1
        
        # 按使用频率排序
        hotspots = sorted(var_usage.items(), key=lambda x: x[1], reverse=True)
        return hotspots[:10]  # 返回前10个热点变量
    
    def generate_coupling_report(self) -> str:
        """生成耦合度分析报告"""
        report = []
        report.append("=== Coupling Analysis Report ===\n")
        
        # 基本统计
        report.append(f"Total Functions: {self.stats['total_functions']}")
        report.append(f"Average Coupling: {self.stats['avg_coupling']:.2f}")
        report.append(f"Maximum Coupling: {self.stats['max_coupling']:.2f}")
        report.append("")
        
        # 耦合度分布
        report.append("Coupling Distribution:")
        for level, count in self.stats['coupling_distribution'].items():
            percentage = count / self.stats['total_functions'] * 100
            report.append(f"  {level.capitalize()}: {count} ({percentage:.1f}%)")
        report.append("")
        
        # 最高耦合函数
        report.append("Top 5 Most Coupled Functions:")
        most_coupled = self.get_most_coupled_functions(5)
        for i, (func, coupling) in enumerate(most_coupled, 1):
            report.append(f"  {i}. {func}: {coupling:.2f}")
        report.append("")
        
        # 不稳定函数
        unstable_funcs = self.get_unstable_functions()
        if unstable_funcs:
            report.append("Highly Unstable Functions:")
            for func in unstable_funcs[:5]:
                metrics = self.coupling_metrics[func]
                report.append(f"  {func}: Instability = {metrics.instability:.3f}")
            report.append("")
        
        # 耦合热点
        hotspots = self.analyze_coupling_hotspots()
        
        if hotspots['coupling_clusters']:
            report.append("Coupling Clusters:")
            for i, cluster in enumerate(hotspots['coupling_clusters'], 1):
                report.append(f"  Cluster {i}: {list(cluster)}")
            report.append("")
        
        if hotspots['global_variable_hotspots']:
            report.append("Global Variable Hotspots:")
            for var, usage_count in hotspots['global_variable_hotspots'][:5]:
                report.append(f"  {var}: used by {usage_count} functions")
        
        return "\n".join(report)
    
    def print_coupling_summary(self):
        """打印耦合度摘要信息"""
        print(self.generate_coupling_report())
        
        # 额外的详细信息
        print("\n=== Detailed Metrics ===")
        
        # 按耦合类型分组统计
        data_couplings = [m.data_coupling for m in self.coupling_metrics.values()]
        control_couplings = [m.control_coupling for m in self.coupling_metrics.values()]
        param_couplings = [m.parameter_coupling for m in self.coupling_metrics.values()]
        global_couplings = [m.global_coupling for m in self.coupling_metrics.values()]
        
        if data_couplings:
            print(f"Data Coupling - Avg: {sum(data_couplings)/len(data_couplings):.2f}, "
                  f"Max: {max(data_couplings)}")
        if control_couplings:
            print(f"Control Coupling - Avg: {sum(control_couplings)/len(control_couplings):.2f}, "
                  f"Max: {max(control_couplings)}")
        if param_couplings:
            print(f"Parameter Coupling - Avg: {sum(param_couplings)/len(param_couplings):.2f}, "
                  f"Max: {max(param_couplings)}")
        if global_couplings:
            print(f"Global Coupling - Avg: {sum(global_couplings)/len(global_couplings):.2f}, "
                  f"Max: {max(global_couplings)}")


class CouplingOptimizer:
    """耦合度优化建议生成器"""
    
    def __init__(self, coupling_calculator: CouplingCalculator):
        self.calculator = coupling_calculator
    
    def generate_optimization_suggestions(self) -> Dict[str, List[str]]:
        """生成优化建议"""
        suggestions = defaultdict(list)
        
        # 分析高耦合函数
        most_coupled = self.calculator.get_most_coupled_functions(10)
        
        for func, coupling_value in most_coupled:
            metrics = self.calculator.get_function_coupling(func)
            if not metrics:
                continue
            
            func_suggestions = []
            
            # 数据耦合优化建议
            if metrics.data_coupling > 5:
                func_suggestions.append(
                    f"High data coupling ({metrics.data_coupling}): "
                    "Consider reducing parameter count or using data structures"
                )
            
            # 全局耦合优化建议
            if metrics.global_coupling > 3:
                func_suggestions.append(
                    f"High global coupling ({metrics.global_coupling}): "
                    "Consider dependency injection or parameter passing"
                )
            
            # 控制耦合优化建议
            if metrics.control_coupling > 2:
                func_suggestions.append(
                    f"High control coupling ({metrics.control_coupling}): "
                    "Consider using polymorphism or strategy pattern"
                )
            
            # 不稳定度建议
            if metrics.instability > 0.8:
                func_suggestions.append(
                    f"High instability ({metrics.instability:.2f}): "
                    "Function is heavily dependent on others, consider refactoring"
                )
            
            if func_suggestions:
                suggestions[func] = func_suggestions
        
        return dict(suggestions)