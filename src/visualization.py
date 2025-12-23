"""可视化模块 - 使用matplotlib和networkx生成依赖关系图"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, List, Tuple, Optional
import networkx as nx
from src.models import DependencyRelation, DependencyType
from src.logger import get_logger


class DependencyVisualizer:
    """依赖关系可视化器"""

    def __init__(self, output_dir: str = "output"):
        self.logger = get_logger(__name__)
        self.logger.info("初始化DependencyVisualizer")
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 依赖类型颜色映射
        self.colors = {
            DependencyType.ASSIGNMENT: "#2C3E50",    # 深蓝
            DependencyType.CONDITION: "#E74C3C",     # 红色
            DependencyType.ARITHMETIC: "#3498DB",    # 蓝色
            DependencyType.POINTER: "#27AE60",       # 绿色
            DependencyType.FUNCTION_CALL: "#F39C12", # 橙色
            DependencyType.RETURN: "#9B59B6",        # 紫色
            DependencyType.COMPARISON: "#7F8C8D"     # 灰色
        }

    def visualize_variable_dependencies(
        self,
        dependencies: List[DependencyRelation],
        var_names: List[str],
        title: str = "Variable Dependency Graph"
    ):
        """
        可视化变量依赖关系图

        Args:
            dependencies: 依赖关系列表
            var_names: 变量名列表
            title: 图表标题
        """
        self.logger.info(f"生成变量依赖关系图: {len(dependencies)} 条关系")

        # 创建有向图
        G = nx.DiGraph()

        # 添加所有变量节点
        for var in var_names:
            G.add_node(var)

        # 添加依赖边（按类型分组）
        edge_colors = []
        edge_labels = {}
        edge_widths = []

        for dep in dependencies:
            if dep.source in var_names and dep.target in var_names:
                # 避免重复边
                if G.has_edge(dep.source, dep.target):
                    # 如果边已存在，更新标签
                    existing_label = edge_labels.get((dep.source, dep.target), "")
                    edge_labels[(dep.source, dep.target)] = f"{existing_label}, {dep.dep_type.value}"
                else:
                    G.add_edge(dep.source, dep.target)
                    edge_colors.append(self.colors.get(dep.dep_type, "#95A5A6"))
                    edge_labels[(dep.source, dep.target)] = dep.dep_type.value
                    edge_widths.append(1.5)

        # 设置图形布局
        plt.figure(figsize=(14, 10))

        # 使用层次布局显示数据流向
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
        except:
            # 如果没有pygraphviz，使用spring布局
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

        # 绘制节点
        node_colors = ["#ECF0F1"] * len(var_names)
        nx.draw_networkx_nodes(
            G, pos,
            node_color=node_colors,
            node_size=2000,
            edgecolors="#34495E",
            linewidths=2,
            alpha=0.9
        )

        # 绘制边
        nx.draw_networkx_edges(
            G, pos,
            edge_color=edge_colors,
            width=edge_widths,
            alpha=0.6,
            arrowstyle="->",
            arrowsize=20,
            connectionstyle="arc3,rad=0.2"
        )

        # 绘制节点标签
        nx.draw_networkx_labels(
            G, pos,
            font_size=10,
            font_weight="bold",
            font_family="monospace"
        )

        # 绘制边标签（简化显示，避免重叠）
        nx.draw_networkx_edge_labels(
            G, pos,
            edge_labels={k: v for k, v in edge_labels.items() if len(G.edges) <= 20},
            font_size=8
        )

        # 添加图例
        legend_patches = []
        for dep_type, color in self.colors.items():
            used = any(d.dep_type == dep_type for d in dependencies)
            if used:
                patch = mpatches.Patch(color=color, label=dep_type.value)
                legend_patches.append(patch)

        if legend_patches:
            plt.legend(
                handles=legend_patches,
                loc='upper left',
                bbox_to_anchor=(1.05, 1),
                borderaxespad=0.
            )

        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "variable_dependencies.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        self.logger.info(f"变量依赖图已保存: {output_path}")

    def visualize_function_calls(
        self,
        func_calls: List[Tuple[str, str]],
        func_names: List[str],
        title: str = "Function Call Graph"
    ):
        """
        可视化函数调用关系图

        Args:
            func_calls: 函数调用关系列表 [(caller, callee), ...]
            func_names: 函数名列表
            title: 图表标题
        """
        self.logger.info(f"生成函数调用关系图: {len(func_calls)} 条关系")

        # 创建有向图
        G = nx.DiGraph()

        # 添加所有函数节点
        for func in func_names:
            G.add_node(func)

        # 添加调用关系边
        for caller, callee in func_calls:
            if caller in func_names and callee in func_names:
                G.add_edge(caller, callee)

        # 设置图形布局
        plt.figure(figsize=(12, 8))

        # 使用层次布局
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
        except:
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

        # 绘制节点
        nx.draw_networkx_nodes(
            G, pos,
            node_color="#3498DB",
            node_size=1500,
            edgecolors="#2C3E50",
            linewidths=2,
            alpha=0.8
        )

        # 绘制边
        nx.draw_networkx_edges(
            G, pos,
            edge_color="#7F8C8D",
            width=2,
            alpha=0.5,
            arrowstyle="->",
            arrowsize=20,
            connectionstyle="arc3,rad=0.1"
        )

        # 绘制标签
        nx.draw_networkx_labels(
            G, pos,
            font_size=9,
            font_weight="bold",
            font_family="monospace"
        )

        plt.title(title, fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "function_calls.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        self.logger.info(f"函数调用图已保存: {output_path}")

    def visualize_adjacency_matrix(
        self,
        matrix: np.ndarray,
        names: List[str],
        title: str = "Dependency Adjacency Matrix",
        is_variable: bool = True
    ):
        """
        可视化邻接矩阵热力图

        Args:
            matrix: 邻接矩阵 (n x n) 或 (n x n x m) 多通道
            names: 节点名称列表
            title: 图表标题
            is_variable: 是否为变量矩阵（影响输出文件名）
        """
        self.logger.info(f"生成邻接矩阵热力图: {matrix.shape}")

        # 如果是多通道矩阵，合并所有通道
        if len(matrix.shape) == 3:
            # 沿着最后一维求和
            display_matrix = matrix.sum(axis=2)
        else:
            display_matrix = matrix

        fig, ax = plt.subplots(figsize=(10, 8))

        # 绘制热力图
        im = ax.imshow(display_matrix, cmap='YlOrRd', aspect='auto')

        # 设置刻度
        ax.set_xticks(range(len(names)))
        ax.set_yticks(range(len(names)))
        ax.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
        ax.set_yticklabels(names, fontsize=8)

        # 添加数值标注
        for i in range(len(names)):
            for j in range(len(names)):
                if display_matrix[i, j] > 0:
                    text = ax.text(
                        j, i, int(display_matrix[i, j]),
                        ha="center", va="center", color="black", fontsize=6
                    )

        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Dependency Count', rotation=270, labelpad=20)

        plt.title(title, fontsize=14, fontweight='bold')
        plt.tight_layout()

        prefix = "variable" if is_variable else "function"
        output_path = os.path.join(self.output_dir, f"{prefix}_matrix.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        self.logger.info(f"邻接矩阵已保存: {output_path}")

    def visualize_combined_graph(
        self,
        var_dependencies: List[DependencyRelation],
        func_calls: List[Tuple[str, str]],
        var_names: List[str],
        func_names: List[str]
    ):
        """
        生成组合视图：变量依赖 + 函数调用关系

        Args:
            var_dependencies: 变量依赖关系
            func_calls: 函数调用关系
            var_names: 变量名列表
            func_names: 函数名列表
        """
        self.logger.info("生成组合关系图")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))

        # 左侧：变量依赖图
        G_var = nx.DiGraph()
        for var in var_names:
            G_var.add_node(var)
        for dep in var_dependencies:
            if dep.source in var_names and dep.target in var_names:
                G_var.add_edge(dep.source, dep.target)

        try:
            pos_var = nx.nx_agraph.graphviz_layout(G_var, prog='dot')
        except:
            pos_var = nx.spring_layout(G_var, k=2, iterations=30, seed=42)

        ax1.set_title("Variable Dependencies", fontsize=14, fontweight='bold')
        nx.draw(G_var, pos_var, ax=ax1, with_labels=True,
                node_color="#ECF0F1", node_size=1500,
                edge_color="#34495E", arrowsize=15,
                font_size=8, font_family='monospace')

        # 右侧：函数调用图
        G_func = nx.DiGraph()
        for func in func_names:
            G_func.add_node(func)
        for caller, callee in func_calls:
            if caller in func_names and callee in func_names:
                G_func.add_edge(caller, callee)

        try:
            pos_func = nx.nx_agraph.graphviz_layout(G_func, prog='dot')
        except:
            pos_func = nx.spring_layout(G_func, k=2, iterations=30, seed=42)

        ax2.set_title("Function Calls", fontsize=14, fontweight='bold')
        nx.draw(G_func, pos_func, ax=ax2, with_labels=True,
                node_color="#3498DB", node_size=1200,
                edge_color="#7F8C8D", arrowsize=15,
                font_size=8, font_family='monospace')

        plt.tight_layout()
        output_path = os.path.join(self.output_dir, "combined_dependencies.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        self.logger.info(f"组合关系图已保存: {output_path}")

    def export_dependency_report(
        self,
        analysis_result: Dict,
        output_path: str = None
    ):
        """
        导出依赖分析报告（文本格式）

        Args:
            analysis_result: DependencyAnalyzer的分析结果
            output_path: 输出文件路径
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, "dependency_report.txt")

        lines = []
        lines.append("=" * 70)
        lines.append("Dependency Analysis Report")
        lines.append("=" * 70)
        lines.append("")

        # 变量统计
        lines.append(f"Total Variables: {len(analysis_result['variable_names'])}")
        lines.append(f"Total Functions: {len(analysis_result['function_names'])}")
        lines.append("")

        # 变量依赖关系统计
        var_deps = analysis_result['variable_dependencies']
        type_count = {}
        for dep in var_deps:
            dtype = dep.dep_type.value
            type_count[dtype] = type_count.get(dtype, 0) + 1

        lines.append("Variable Dependencies by Type:")
        for dtype, count in sorted(type_count.items(), key=lambda x: -x[1]):
            lines.append(f"  - {dtype}: {count}")
        lines.append("")

        # 函数调用关系统计
        func_calls = analysis_result['function_dependencies']
        lines.append(f"Total Function Calls: {len(func_calls)}")
        lines.append("")

        # 列出所有变量依赖关系
        lines.append("Variable Dependency Details:")
        lines.append("-" * 70)
        for dep in var_deps:
            lines.append(
                f"  {dep.source} --[{dep.dep_type.value}]--> {dep.target} "
                f"(context: {dep.context})"
            )
        lines.append("")

        # 列出所有函数调用关系
        lines.append("Function Call Details:")
        lines.append("-" * 70)
        for caller, callee in func_calls:
            lines.append(f"  {caller} --> {callee}")
        lines.append("")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        self.logger.info(f"依赖分析报告已保存: {output_path}")
