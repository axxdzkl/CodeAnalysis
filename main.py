import json
import logging
import os
import sys
from pathlib import Path
from src.ast_parser import CCodeParser
from src.llm_engine import SemanticDeriver
from src.dependency_analyzer import DependencyAnalyzer
from src.visualization import DependencyVisualizer
from src.logger import Logger, get_logger


def load_code(filepath):
    """加载C代码文件"""
    logger = get_logger(__name__)
    logger.debug(f"加载C代码文件: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        logger.info(f"成功加载C代码: {filepath}, 代码长度: {len(code)} 字符")
        return code
    except FileNotFoundError:
        logger.error(f"文件不存在: {filepath}")
        raise
    except Exception as e:
        logger.error(f"加载文件失败 {filepath}: {e}")
        raise


def load_json(filepath):
    """加载JSON配置文件"""
    logger = get_logger(__name__)
    logger.debug(f"加载JSON配置: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"成功加载配置: {filepath}")
        logger.debug(f"配置内容: {config}")
        return config
    except FileNotFoundError:
        logger.error(f"配置文件不存在: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败 {filepath}: {e}")
        raise
    except Exception as e:
        logger.error(f"加载配置失败 {filepath}: {e}")
        raise


def save_result(filepath, result):
    """保存结果到文件"""
    logger = get_logger(__name__)
    logger.debug(f"保存结果到: {filepath}")

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"结果已保存至: {filepath}")
    except Exception as e:
        logger.error(f"保存结果失败: {e}")
        raise


def main():
    """主函数"""
    logger = get_logger(__name__)
    logger.info("=" * 60)
    logger.info("C语义推导器启动")
    logger.info("=" * 60)

    try:
        # 1. 配置与输入
        code_path = "config/input_code.c"
        anchors_path = "config/anchors.json"

        logger.info(f"输入配置: C代码={code_path}, 锚点配置={anchors_path}")

        print(f"[*] 正在解析C代码: {code_path}...")
        code = load_code(code_path)
        anchors_config = load_json(anchors_path)

        # 2. 语法解析 -> 构建范畴
        logger.info("开始AST解析阶段")
        parser = CCodeParser()
        context = parser.parse(code)

        print(f"    |-> 发现函数: {list(context.functions.keys())}")
        print(f"    |-> 发现变量: {list(context.variables.keys())}")
        print(f"    |-> 发现变量依赖关系: {len(context.variable_dependencies)} 条")
        print(f"    |-> 发现函数调用关系: {len(context.function_calls)} 条")

        logger.info(f"AST解析完成，发现 {len(context.functions)} 个函数")

        # 3. 依赖关系分析
        logger.info("开始依赖关系分析阶段")
        print(f"[*] 正在分析变量和函数依赖关系...")

        analyzer = DependencyAnalyzer()
        analysis_result = analyzer.analyze_dependencies(context)

        print(f"    |-> 变量依赖矩阵: {analysis_result['variable_matrix'].shape}")
        print(f"    |-> 函数调用矩阵: {analysis_result['function_matrix'].shape}")

        # 生成依赖分析报告
        summary = analyzer.get_dependency_summary(analysis_result['variable_dependencies'])
        print(f"    |-> 依赖关系统计: {summary}")

        # 4. 生成可视化图表
        logger.info("开始生成可视化图表")
        print(f"[*] 正在生成依赖关系可视化...")

        visualizer = DependencyVisualizer(output_dir="output")

        # 生成变量依赖图
        if analysis_result['variable_dependencies']:
            visualizer.visualize_variable_dependencies(
                analysis_result['variable_dependencies'],
                analysis_result['variable_names']
            )
            print(f"    |-> 变量依赖图: output/variable_dependencies.png")

        # 生成函数调用图
        if analysis_result['function_dependencies']:
            visualizer.visualize_function_calls(
                analysis_result['function_dependencies'],
                analysis_result['function_names']
            )
            print(f"    |-> 函数调用图: output/function_calls.png")

        # 生成邻接矩阵热力图
        if len(context.variables) > 0:
            visualizer.visualize_adjacency_matrix(
                analysis_result['variable_matrix'],
                analysis_result['variable_names'],
                "Variable Dependency Matrix",
                is_variable=True
            )
            print(f"    |-> 变量邻接矩阵: output/variable_matrix.png")

        if len(context.functions) > 0:
            visualizer.visualize_adjacency_matrix(
                analysis_result['function_matrix'],
                analysis_result['function_names'],
                "Function Call Matrix",
                is_variable=False
            )
            print(f"    |-> 函数邻接矩阵: output/function_matrix.png")

        # 生成组合视图
        if (analysis_result['variable_dependencies'] and
            analysis_result['function_dependencies']):
            visualizer.visualize_combined_graph(
                analysis_result['variable_dependencies'],
                analysis_result['function_dependencies'],
                analysis_result['variable_names'],
                analysis_result['function_names']
            )
            print(f"    |-> 组合关系图: output/combined_dependencies.png")

        # 导出依赖分析报告
        visualizer.export_dependency_report(analysis_result)
        print(f"    |-> 依赖分析报告: output/dependency_report.txt")

        # 导出DOT文件（可选，用于Graphviz）
        if analysis_result['variable_dependencies']:
            analyzer.export_to_dot(
                analysis_result['variable_dependencies'],
                analysis_result['variable_names'],
                "output/variable_dependencies.dot"
            )
            print(f"    |-> DOT文件: output/variable_dependencies.dot")

        # 5. LLM语义推导
        logger.info("开始LLM语义推导阶段")
        print(f"[*] 正在调用LLM进行语义推导...")

        deriver = SemanticDeriver()
        result = deriver.derive_semantics(context, anchors_config)

        # 检查是否有错误
        if "error" in result:
            logger.error(f"语义推导失败: {result['error']}")
            print(f"\n[错误] 语义推导失败: {result['error']}")
            return 1

        # 6. 输出结果
        logger.info("语义推导成功，准备输出结果")

        print("\n" + "=" * 30)
        print("语义推导结果")
        print("=" * 30)
        print(json.dumps(result, ensure_ascii=False, indent=2))

        # 持久化保存
        output_path = "output/result.json"
        save_result(output_path, result)
        print("\n[+] 结果已保存至 output/result.json")

        # 保存依赖分析结果
        dep_analysis_path = "output/dependency_analysis.json"
        # 转换numpy数组为列表以便JSON序列化
        save_analysis = {
            "variable_dependencies": [
                {
                    "source": d.source,
                    "target": d.target,
                    "type": d.dep_type.value,
                    "context": d.context,
                    "line": d.line_number
                }
                for d in analysis_result['variable_dependencies']
            ],
            "function_dependencies": analysis_result['function_dependencies'],
            "variable_names": analysis_result['variable_names'],
            "function_names": analysis_result['function_names'],
            "variable_matrix": analysis_result['variable_matrix'].tolist(),
            "function_matrix": analysis_result['function_matrix'].tolist()
        }
        save_result(dep_analysis_path, save_analysis)
        print("[+] 依赖分析结果已保存至 output/dependency_analysis.json")

        logger.info("=" * 60)
        logger.info("C语义推导器执行完成")
        logger.info("=" * 60)
        return 0

    except FileNotFoundError as e:
        logger.error(f"文件错误: {e}")
        print(f"\n[错误] 文件未找到: {e}")
        return 1

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        print(f"\n[错误] JSON解析失败: {e}")
        return 1

    except Exception as e:
        logger.error(f"程序执行异常: {e}", exc_info=True)
        print(f"\n[错误] 程序执行失败: {e}")
        return 1


if __name__ == "__main__":
    # 确保输出目录存在
    if not os.path.exists("output"):
        os.makedirs("output")

    # 初始化日志系统
    Logger.setup(
        log_dir="logs",
        log_level=logging.INFO,  # 可改为 logging.DEBUG 查看更详细日志
        console_output=True
    )

    # 运行主程序并退出
    sys.exit(main())
