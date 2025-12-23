import json
import os
import time
from openai import OpenAI
from src.models import CategoryContext, DependencyType
from src.logger import get_logger
from typing import Dict, List


class SemanticDeriver:
    """基于LLM的语义推导引擎"""

    def __init__(self, api_key: str = None, base_url: str = "https://ark.cn-beijing.volces.com/api/v3"):
        self.logger = get_logger(__name__)
        self.logger.info("初始化SemanticDeriver")

        # 从参数或环境变量获取API Key
        if api_key is None:
            api_key = os.environ.get("ARK_API_KEY", "a4c067f2-5829-4f38-94cd-91fd5b6a9984")

        self.api_key = api_key[:8] + "..." if len(api_key) > 8 else "***"  # 隐藏完整key
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = "deepseek-r1-250528"
        self.base_url = base_url

        self.logger.info(f"LLM配置: model={self.model}, base_url={base_url}, api_key={self.api_key}")

    def derive_semantics(self, context: CategoryContext, anchors_config: dict) -> dict:
        """
        基于范畴上下文和语义锚点推导语义

        Args:
            context: 范畴上下文，包含函数和变量信息
            anchors_config: 语义锚点配置

        Returns:
            dict: 语义推导结果
        """
        self.logger.info("开始语义推导")
        self.logger.debug(f"语义锚点: {anchors_config}")

        # 1. 将AST结构转化为LLM易读的文本表示
        structure_text = self._serialize_context(context)
        self.logger.debug(f"范畴结构文本长度: {len(structure_text)} 字符")

        # 2. 构造Prompt（核心：范畴论思想）
        prompt = f"""
你是一个精通C语言和范畴论的语义分析专家。
现在的任务是基于"外延定义"原则，通过已知的语义锚点和代码语法关系（态射），推导未知对象的业务含义。

【范畴对象与态射图谱】
{structure_text}

【语义锚点】
{json.dumps(anchors_config, ensure_ascii=False)}

【推导规则】
1. 变量的语义由其与锚点变量的数据流向关系（赋值、指针传递、计算）决定。
2. 函数的语义由其输入/输出变量（锚点）及它对变量的操作（加/减/过滤/传输）决定。
3. 指针通常代表引用传递或数组流，Const指针代表只读配置或源数据。
4. 保持语义闭环：如果变量B是锚点变量A的平方结果，则B是"A的计算衍生值"。

请输出结构化的JSON结果，包含以下字段：
{{
  "variable_meaning": [{{"name": "var_name", "semantic": "业务含义", "type": "数据类型/角色"}}],
  "function_meaning": [{{"name": "func_name", "semantic": "核心功能", "role": "upstream/downstream/processor"}}],
  "function_relations": "描述函数间的调用层级和数据流向",
  "global_logic": "基于输入到输出的完整业务流程总结"
}}
"""

        # 3. 调用LLM
        try:
            self.logger.info(f"调用LLM进行语义推导，模型: {self.model}")
            start_time = time.time()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个严谨的代码语义分析引擎，只输出JSON格式的结果，不要包含任何其他文字说明。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )

            elapsed_time = time.time() - start_time
            content = response.choices[0].message.content

            # 记录token使用情况（如果API返回）
            if hasattr(response, 'usage') and response.usage:
                self.logger.info(
                    f"LLM调用完成，耗时: {elapsed_time:.2f}秒, "
                    f"输入tokens: {response.usage.prompt_tokens}, "
                    f"输出tokens: {response.usage.completion_tokens}, "
                    f"总tokens: {response.usage.total_tokens}"
                )
            else:
                self.logger.info(f"LLM调用完成，耗时: {elapsed_time:.2f}秒")

            self.logger.debug(f"LLM响应长度: {len(content)} 字符")

            result = json.loads(content)
            self.logger.info(f"语义推导成功，解析出 {len(result.get('variable_meaning', []))} 个变量语义, "
                           f"{len(result.get('function_meaning', []))} 个函数语义")

            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}", exc_info=True)
            self.logger.debug(f"原始响应内容: {content[:500] if content else 'empty'}...")
            return {"error": f"JSON解析失败: {str(e)}"}

        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}", exc_info=True)
            return {"error": str(e)}

    def _serialize_context(self, context: CategoryContext) -> str:
        """
        将CategoryContext序列化为描述性文本（包含依赖关系）

        Args:
            context: 范畴上下文

        Returns:
            str: 序列化的文本描述
        """
        lines = []
        lines.append("--- 函数对象 ---")
        for fname, fnode in context.functions.items():
            defined = f", 定义变量: {fnode.defined_vars}" if fnode.defined_vars else ""
            lines.append(
                f"函数: {fname} | 参数: {fnode.parameters} | 调用: {fnode.calls} | 访问变量: {fnode.vars_accessed}{defined}")

        lines.append("\n--- 变量对象 ---")
        for var_name, var_node in context.variables.items():
            deps = []
            for dep_var, dep_types in var_node.depends_on.items():
                type_strs = [t.value for t in dep_types]
                deps.append(f"{dep_var}({','.join(type_strs)})")
            dep_str = f" 依赖: {deps}" if deps else ""
            lines.append(f"变量: {var_name} | 作用域: {var_node.scope} | 类型: {var_node.type}{dep_str}")

        lines.append("\n--- 变量依赖关系态射 ---")
        # 按依赖类型分组展示
        dep_by_type: Dict[DependencyType, List] = {dt: [] for dt in DependencyType}
        for dep in context.variable_dependencies:
            dep_by_type[dep.dep_type].append(dep)

        for dep_type, deps in dep_by_type.items():
            if deps:
                lines.append(f"\n[{dep_type.value.upper()} 依赖]")
                for dep in deps[:20]:  # 限制数量避免过长
                    lines.append(f"  {dep.source} --[{dep_type.value}]--> {dep.target} (上下文: {dep.context})")
                if len(deps) > 20:
                    lines.append(f"  ... 还有 {len(deps) - 20} 条 {dep_type.value} 依赖")

        lines.append("\n--- 函数调用关系 ---")
        for caller, callee in context.function_calls:
            lines.append(f"  {caller} --> {callee}")

        lines.append("\n--- 函数-变量操作态射 ---")
        # 简单的共现分析展示给LLM
        for fname, fnode in context.functions.items():
            for var in fnode.vars_accessed:
                lines.append(f"  函数 '{fname}' <操作> 变量 '{var}'")

        return "\n".join(lines)

    def serialize_dependency_analysis(self, analysis_result: Dict) -> str:
        """
        序列化依赖分析结果为文本

        Args:
            analysis_result: DependencyAnalyzer的分析结果

        Returns:
            str: 序列化的依赖分析文本
        """
        lines = []
        lines.append("--- 依赖关系矩阵分析 ---")

        # 变量依赖矩阵摘要
        var_matrix = analysis_result.get('variable_matrix')
        if var_matrix is not None:
            if len(var_matrix.shape) == 3:
                total_deps = var_matrix.sum()
                lines.append(f"\n变量依赖矩阵: {var_matrix.shape[0]} x {var_matrix.shape[1]} x {var_matrix.shape[2]}")
                lines.append(f"总依赖关系数: {int(total_deps)}")
            else:
                total_deps = var_matrix.sum()
                lines.append(f"\n变量依赖矩阵: {var_matrix.shape[0]} x {var_matrix.shape[1]}")
                lines.append(f"总依赖关系数: {int(total_deps)}")

        # 函数调用矩阵摘要
        func_matrix = analysis_result.get('function_matrix')
        if func_matrix is not None:
            total_calls = func_matrix.sum()
            lines.append(f"\n函数调用矩阵: {func_matrix.shape[0]} x {func_matrix.shape[1]}")
            lines.append(f"总调用关系数: {int(total_calls)}")

        # 依赖类型统计
        var_deps = analysis_result.get('variable_dependencies', [])
        type_count = {}
        for dep in var_deps:
            dtype = dep.dep_type.value
            type_count[dtype] = type_count.get(dtype, 0) + 1

        if type_count:
            lines.append("\n依赖类型统计:")
            for dtype, count in sorted(type_count.items(), key=lambda x: -x[1]):
                lines.append(f"  {dtype}: {count}")

        return "\n".join(lines)
