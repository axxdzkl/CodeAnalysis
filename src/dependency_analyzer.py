"""依赖关系分析器 - 构建变量间和函数间的依赖关系图"""
import numpy as np
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from src.models import CategoryContext, DependencyRelation, DependencyType
from src.logger import get_logger


class DependencyAnalyzer:
    """依赖关系分析器"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("初始化DependencyAnalyzer")

    def analyze_dependencies(self, context: CategoryContext) -> Dict:
        """
        分析上下文中的所有依赖关系

        Args:
            context: 范畴上下文

        Returns:
            Dict: 包含依赖关系矩阵和分析结果的字典
        """
        self.logger.info("开始分析依赖关系")

        # 分析变量依赖关系
        var_deps = self._build_variable_dependencies(context)

        # 分析函数调用关系
        func_calls = self._build_function_dependencies(context)

        # 构建有向邻接矩阵
        var_matrix = self._build_variable_matrix(context, var_deps)
        func_matrix = self._build_function_matrix(context, func_calls)

        result = {
            "variable_dependencies": var_deps,
            "function_dependencies": func_calls,
            "variable_matrix": var_matrix,
            "function_matrix": func_matrix,
            "variable_names": list(context.variables.keys()),
            "function_names": list(context.functions.keys())
        }

        self.logger.info(
            f"依赖分析完成: 变量关系 {len(var_deps)} 条, "
            f"函数关系 {len(func_calls)} 条"
        )

        return result

    def _build_variable_dependencies(self, context: CategoryContext) -> List[DependencyRelation]:
        """从CategoryContext中提取变量依赖关系"""
        dependencies = []

        # 从已有的variable_dependencies中提取
        for rel in context.variable_dependencies:
            dependencies.append(rel)

        # 从变量节点的depends_on中补充
        for var_name, var_node in context.variables.items():
            for dep_var, dep_types in var_node.depends_on.items():
                for dep_type in dep_types:
                    # 避免重复添加
                    exists = any(
                        d.source == var_name and d.target == dep_var and d.dep_type == dep_type
                        for d in dependencies
                    )
                    if not exists:
                        dependencies.append(DependencyRelation(
                            source=var_name,
                            target=dep_var,
                            dep_type=dep_type,
                            context=var_node.scope
                        ))

        self.logger.debug(f"构建变量依赖关系: {len(dependencies)} 条")
        return dependencies

    def _build_function_dependencies(self, context: CategoryContext) -> List[Tuple[str, str]]:
        """从CategoryContext中提取函数调用关系"""
        dependencies = []

        for func_name, func_node in context.functions.items():
            for called_func in func_node.calls:
                dependencies.append((func_name, called_func))

        self.logger.debug(f"构建函数调用关系: {len(dependencies)} 条")
        return dependencies

    def _build_variable_matrix(
        self,
        context: CategoryContext,
        dependencies: List[DependencyRelation]
    ) -> np.ndarray:
        """
        构建变量依赖关系的邻接矩阵

        Returns:
            np.ndarray: n x n 矩阵，matrix[i][j] 表示从变量i到变量j的依赖类型数量
        """
        var_names = list(context.variables.keys())
        n = len(var_names)
        var_index = {name: i for i, name in enumerate(var_names)}

        # 创建多维矩阵：每种依赖类型一个通道
        matrix = np.zeros((n, n, len(DependencyType)), dtype=int)

        for dep in dependencies:
            if dep.source in var_index and dep.target in var_index:
                i = var_index[dep.source]
                j = var_index[dep.target]
                dep_type_idx = list(DependencyType).index(dep.dep_type)
                matrix[i][j][dep_type_idx] += 1

        self.logger.debug(f"变量依赖矩阵形状: {matrix.shape}")
        return matrix

    def _build_function_matrix(
        self,
        context: CategoryContext,
        dependencies: List[Tuple[str, str]]
    ) -> np.ndarray:
        """
        构建函数调用关系的邻接矩阵

        Returns:
            np.ndarray: n x n 矩阵，matrix[i][j] = 1 表示函数i调用函数j
        """
        func_names = list(context.functions.keys())
        n = len(func_names)
        func_index = {name: i for i, name in enumerate(func_names)}

        matrix = np.zeros((n, n), dtype=int)

        for caller, callee in dependencies:
            if caller in func_index and callee in func_index:
                i = func_index[caller]
                j = func_index[callee]
                matrix[i][j] += 1

        self.logger.debug(f"函数调用矩阵形状: {matrix.shape}")
        return matrix

    def get_dependency_summary(self, dependencies: List[DependencyRelation]) -> Dict:
        """获取依赖关系统计摘要"""
        summary = defaultdict(int)
        type_count = defaultdict(int)

        for dep in dependencies:
            summary[dep.source] += 1
            type_count[dep.dep_type.value] += 1

        return {
            "total_dependencies": len(dependencies),
            "by_type": dict(type_count),
            "by_variable": dict(summary),
            "most_dependent": max(summary.items(), key=lambda x: x[1])[0] if summary else None
        }

    def export_to_dot(
        self,
        dependencies: List[DependencyRelation],
        var_names: List[str],
        output_path: str
    ):
        """导出依赖关系到DOT格式（用于Graphviz）"""
        lines = ["digraph VariableDependencies {"]
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box];')

        # 添加节点
        for var in var_names:
            lines.append(f'  "{var}";')

        # 添加边（按类型分组着色）
        colors = {
            DependencyType.ASSIGNMENT: "black",
            DependencyType.CONDITION: "red",
            DependencyType.ARITHMETIC: "blue",
            DependencyType.POINTER: "green",
            DependencyType.FUNCTION_CALL: "orange",
            DependencyType.RETURN: "purple",
            DependencyType.COMPARISON: "brown"
        }

        for dep in dependencies:
            color = colors.get(dep.dep_type, "gray")
            label = dep.dep_type.value
            lines.append(
                f'  "{dep.source}" -> "{dep.target}" '
                f'[label="{label}", color={color}];'
            )

        lines.append("}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        self.logger.info(f"DOT文件已导出: {output_path}")

    def get_path_dependencies(
        self,
        source: str,
        target: str,
        dependencies: List[DependencyRelation]
    ) -> List[List[str]]:
        """
        查找从source到target的所有依赖路径（BFS）

        Returns:
            List[List[str]]: 依赖路径列表，每条路径是变量名序列
        """
        # 构建邻接表
        graph = defaultdict(list)
        for dep in dependencies:
            graph[dep.source].append(dep.target)

        # BFS查找路径
        paths = []
        queue = [(source, [source])]
        visited = set()

        while queue:
            node, path = queue.pop(0)

            if node == target:
                paths.append(path)
                continue

            if node in visited:
                continue
            visited.add(node)

            for neighbor in graph[node]:
                if neighbor not in path:  # 避免循环
                    queue.append((neighbor, path + [neighbor]))

        return paths
