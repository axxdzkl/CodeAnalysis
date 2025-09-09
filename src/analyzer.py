"""
主分析器模块

本模块是整个C语言静态分析系统的核心，集成了所有分析功能：
- CFG构建
- 数据流分析
- PDG构建
- 函数调用图分析
- 函数间分析
- 耦合度计算
- 结果可视化
"""

import clang.cindex
import networkx as nx
from typing import Dict, List, Any, Optional
import logging
import os
import sys
from pathlib import Path

# 导入各个分析模块
try:
    # 尝试相对导入
    from .cfg import CFGBuilder
    from .dataflow import DataFlowAnalyzer
    from .pdg import PDGBuilder
    from .callgraph import CallGraphBuilder
    from .interprocedural import InterproceduralAnalyzer
    from .coupling import CouplingCalculator
    from .visualization import SourceMapper, GraphVisualizer
except ImportError:
    # 回退到绝对导入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from cfg import CFGBuilder
    from dataflow import DataFlowAnalyzer
    from pdg import PDGBuilder
    from callgraph import CallGraphBuilder
    from interprocedural import InterproceduralAnalyzer
    from coupling import CouplingCalculator
    from visualization import SourceMapper, GraphVisualizer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CStaticAnalyzer:
    """C语言静态分析器主类"""
    
    def __init__(self, source_file: str, include_paths: Optional[List[str]] = None):
        """
        初始化静态分析器
        
        Args:
            source_file: C源文件路径
            include_paths: 包含路径列表
        """
        self.source_file = os.path.abspath(source_file)
        self.include_paths = include_paths or []
        
        # 验证文件存在
        if not os.path.exists(self.source_file):
            raise FileNotFoundError(f"Source file not found: {self.source_file}")
        
        # 初始化Clang
        self.index = clang.cindex.Index.create()
        self.tu = None
        
        # 分析结果存储
        self.results = {
            'cfgs': {},
            'dataflow': None,
            'pdgs': {},
            'call_graph': None,
            'interprocedural': None,
            'coupling': None,
            'source_map': None
        }
        
        # 分析器组件
        self.cfg_builder = None
        self.dataflow_analyzer = None
        self.pdg_builders = {}
        self.call_graph_builder = None
        self.interprocedural_analyzer = None
        self.coupling_calculator = None
        self.source_mapper = None
        self.graph_visualizer = None
        
        # 配置Clang解析选项
        self.clang_args = [
            '-std=c11',
            '-Wall',
            '-Wextra'
        ]
        
        # 添加包含路径
        for include_path in self.include_paths:
            self.clang_args.append(f'-I{include_path}')
        
        logger.info(f"Initialized analyzer for {self.source_file}")
    
    def analyze(self) -> Dict[str, Any]:
        """
        执行完整的静态分析流程
        
        Returns:
            Dict[str, Any]: 分析结果
        """
        logger.info("Starting comprehensive static analysis...")
        
        try:
            # 1. 解析源文件
            self._parse_source()
            
            # 2. 构建控制流图
            self._build_control_flow_graphs()
            
            # 3. 执行数据流分析
            self._perform_dataflow_analysis()
            
            # 4. 构建程序依赖图
            self._build_program_dependence_graphs()
            
            # 5. 构建函数调用图
            self._build_call_graph()
            
            # 6. 执行函数间分析
            self._perform_interprocedural_analysis()
            
            # 7. 计算耦合度
            self._calculate_coupling_metrics()
            
            # 8. 构建源码映射
            self._build_source_mapping()
            
            logger.info("Static analysis completed successfully")
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise
        
        return self.results
    
    def _parse_source(self):
        """解析C源文件"""
        logger.info("Parsing source file...")
        
        try:
            self.tu = self.index.parse(
                self.source_file,
                args=self.clang_args,
                options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
            )
            
            if not self.tu:
                raise RuntimeError("Failed to parse source file")
            
            # 检查解析错误
            diagnostics = list(self.tu.diagnostics)
            errors = [d for d in diagnostics if d.severity >= clang.cindex.Diagnostic.Error]
            
            if errors:
                logger.error("Parse errors found:")
                for error in errors[:5]:  # 显示前5个错误
                    logger.error(f"  {error.location}: {error.spelling}")
                raise RuntimeError(f"Source file has {len(errors)} parse errors")
            
            warnings = [d for d in diagnostics if d.severity == clang.cindex.Diagnostic.Warning]
            if warnings:
                logger.warning(f"Found {len(warnings)} warnings during parsing")
            
            logger.info("Source file parsed successfully")
            
        except Exception as e:
            logger.error(f"Failed to parse source file: {e}")
            raise
    
    def _build_control_flow_graphs(self):
        """构建控制流图"""
        logger.info("Building control flow graphs...")
        
        try:
            self.cfg_builder = CFGBuilder(self.source_file)
            function_cfgs = self.cfg_builder.build_cfg()
            
            self.results['cfgs'] = function_cfgs
            
            # 打印统计信息
            total_blocks = sum(cfg.number_of_nodes() for cfg in function_cfgs.values())
            total_edges = sum(cfg.number_of_edges() for cfg in function_cfgs.values())
            
            logger.info(f"Built CFGs for {len(function_cfgs)} functions")
            logger.info(f"Total basic blocks: {total_blocks}")
            logger.info(f"Total CFG edges: {total_edges}")
            
        except Exception as e:
            logger.error(f"CFG construction failed: {e}")
            raise
    
    def _perform_dataflow_analysis(self):
        """执行数据流分析"""
        logger.info("Performing dataflow analysis...")
        
        try:
            # 对每个函数的CFG执行数据流分析
            function_dataflow_results = {}
            
            for func_name, cfg in self.results['cfgs'].items():
                logger.info(f"Analyzing dataflow for function: {func_name}")
                
                analyzer = DataFlowAnalyzer(cfg)
                dataflow_result = analyzer.analyze()
                
                function_dataflow_results[func_name] = dataflow_result
            
            # 合并所有函数的数据流分析结果
            self.results['dataflow'] = self._merge_dataflow_results(function_dataflow_results)
            
            logger.info("Dataflow analysis completed")
            
        except Exception as e:
            logger.error(f"Dataflow analysis failed: {e}")
            raise
    
    def _build_program_dependence_graphs(self):
        """构建程序依赖图"""
        logger.info("Building program dependence graphs...")
        
        try:
            function_pdgs = {}
            
            for func_name, cfg in self.results['cfgs'].items():
                logger.info(f"Building PDG for function: {func_name}")
                
                # 获取该函数的数据流分析结果
                func_dataflow = self.results['dataflow']
                
                pdg_builder = PDGBuilder(cfg, func_dataflow)
                pdg = pdg_builder.build_pdg()
                
                function_pdgs[func_name] = pdg
                self.pdg_builders[func_name] = pdg_builder
            
            self.results['pdgs'] = function_pdgs
            
            # 统计信息
            total_nodes = sum(pdg.number_of_nodes() for pdg in function_pdgs.values())
            total_edges = sum(pdg.number_of_edges() for pdg in function_pdgs.values())
            
            logger.info(f"Built PDGs for {len(function_pdgs)} functions")
            logger.info(f"Total PDG nodes: {total_nodes}")
            logger.info(f"Total PDG edges: {total_edges}")
            
        except Exception as e:
            logger.error(f"PDG construction failed: {e}")
            raise
    
    def _build_call_graph(self):
        """构建函数调用图"""
        logger.info("Building function call graph...")
        
        try:
            self.call_graph_builder = CallGraphBuilder(self.tu)
            call_graph = self.call_graph_builder.build_call_graph()
            
            self.results['call_graph'] = call_graph
            
            # 打印统计信息
            self.call_graph_builder.print_call_graph_summary()
            
            logger.info("Call graph construction completed")
            
        except Exception as e:
            logger.error(f"Call graph construction failed: {e}")
            raise
    
    def _perform_interprocedural_analysis(self):
        """执行函数间分析"""
        logger.info("Performing interprocedural analysis...")
        
        try:
            call_graph = self.results['call_graph']
            pdgs = self.results['pdgs']
            
            self.interprocedural_analyzer = InterproceduralAnalyzer(call_graph, pdgs)
            interprocedural_result = self.interprocedural_analyzer.analyze()
            
            self.results['interprocedural'] = interprocedural_result
            
            # 打印统计信息
            self.interprocedural_analyzer.print_interprocedural_summary()
            
            logger.info("Interprocedural analysis completed")
            
        except Exception as e:
            logger.error(f"Interprocedural analysis failed: {e}")
            raise
    
    def _calculate_coupling_metrics(self):
        """计算耦合度指标"""
        logger.info("Calculating coupling metrics...")
        
        try:
            call_graph = self.results['call_graph']
            interprocedural_result = self.results['interprocedural']
            
            self.coupling_calculator = CouplingCalculator(call_graph, interprocedural_result)
            coupling_result = self.coupling_calculator.calculate_coupling()
            
            self.results['coupling'] = coupling_result
            
            # 打印统计信息
            self.coupling_calculator.print_coupling_summary()
            
            logger.info("Coupling metrics calculation completed")
            
        except Exception as e:
            logger.error(f"Coupling calculation failed: {e}")
            raise
    
    def _build_source_mapping(self):
        """构建源码映射"""
        logger.info("Building source mapping...")
        
        try:
            self.source_mapper = SourceMapper(self.tu)
            source_map = self.source_mapper.build_source_map(self.results)
            
            self.results['source_map'] = source_map
            
            logger.info(f"Built source mapping with {len(source_map)} entries")
            
        except Exception as e:
            logger.error(f"Source mapping failed: {e}")
            raise
    
    def _merge_dataflow_results(self, function_results: Dict[str, Any]) -> Dict[str, Any]:
        """合并多个函数的数据流分析结果"""
        merged = {
            'reaching_definitions': {'in': {}, 'out': {}},
            'live_variables': {'in': {}, 'out': {}},
            'available_expressions': {'in': {}, 'out': {}},
            'definitions': set(),
            'variables': set()
        }
        
        for func_name, result in function_results.items():
            # 合并到达定值
            rd = result.get('reaching_definitions', {})
            if 'in' in rd:
                merged['reaching_definitions']['in'].update(rd['in'])
            if 'out' in rd:
                merged['reaching_definitions']['out'].update(rd['out'])
            
            # 合并活跃变量
            lv = result.get('live_variables', {})
            if 'in' in lv:
                merged['live_variables']['in'].update(lv['in'])
            if 'out' in lv:
                merged['live_variables']['out'].update(lv['out'])
            
            # 合并可用表达式
            ae = result.get('available_expressions', {})
            if 'in' in ae:
                merged['available_expressions']['in'].update(ae['in'])
            if 'out' in ae:
                merged['available_expressions']['out'].update(ae['out'])
            
            # 合并定义和变量
            merged['definitions'].update(result.get('definitions', set()))
            merged['variables'].update(result.get('variables', set()))
        
        return merged
    
    def visualize_graphs(self) -> Dict[str, List[str]]:
        """生成分析图的可视化"""
        logger.info("Generating visualizations...")
        
        try:
            self.graph_visualizer = GraphVisualizer()
            generated_files = {
                'cfg_files': [],
                'pdg_files': [],
                'call_graph_file': '',
                'coupling_heatmap_file': ''
            }
            
            # 可视化CFG
            for func_name, cfg in self.results['cfgs'].items():
                cfg_file = self.graph_visualizer.visualize_cfg(cfg, func_name)
                if cfg_file:
                    generated_files['cfg_files'].append(cfg_file)
            
            # 可视化调用图
            call_graph = self.results['call_graph']
            if call_graph:
                cg_file = self.graph_visualizer.visualize_call_graph(call_graph)
                generated_files['call_graph_file'] = cg_file
            
            # 可视化耦合度热力图
            coupling_result = self.results.get('coupling', {})
            coupling_matrix = coupling_result.get('matrix', {})
            if coupling_matrix:
                functions = list(self.results['cfgs'].keys())
                heatmap_file = self.graph_visualizer.visualize_coupling_heatmap(
                    coupling_matrix, functions
                )
                generated_files['coupling_heatmap_file'] = heatmap_file
            
            logger.info(f"Generated {len(generated_files['cfg_files'])} CFG visualizations")
            logger.info(f"Generated call graph: {bool(generated_files['call_graph_file'])}")
            logger.info(f"Generated coupling heatmap: {bool(generated_files['coupling_heatmap_file'])}")
            
            return generated_files
            
        except Exception as e:
            logger.error(f"Visualization failed: {e}")
            return {'cfg_files': [], 'pdg_files': [], 'call_graph_file': '', 'coupling_heatmap_file': ''}
    
    def generate_report(self) -> str:
        """生成HTML分析报告"""
        logger.info("Generating analysis report...")
        
        try:
            if not self.source_mapper:
                self.source_mapper = SourceMapper(self.tu)
            
            report_html = self.source_mapper.generate_html_report(self.results)
            
            # 保存报告到文件
            output_dir = "analysis_output"
            os.makedirs(output_dir, exist_ok=True)
            report_path = os.path.join(output_dir, "analysis_report.html")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_html)
            
            logger.info(f"Analysis report generated: {report_path}")
            
            return report_html
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return ""
    
    def export_results(self, output_format: str = 'json') -> str:
        """导出分析结果"""
        logger.info(f"Exporting results in {output_format} format...")
        
        try:
            output_dir = "analysis_output"
            os.makedirs(output_dir, exist_ok=True)
            
            if output_format == 'json':
                import json
                
                # 准备可序列化的数据
                export_data = {
                    'source_file': self.source_file,
                    'functions': list(self.results['cfgs'].keys()),
                    'statistics': {
                        'total_functions': len(self.results['cfgs']),
                        'total_blocks': sum(cfg.number_of_nodes() for cfg in self.results['cfgs'].values()),
                        'total_calls': self.results['call_graph'].number_of_edges() if self.results['call_graph'] else 0,
                    }
                }
                
                # 添加耦合度统计
                coupling_result = self.results.get('coupling', {})
                if coupling_result.get('statistics'):
                    export_data['coupling_statistics'] = coupling_result['statistics']
                
                output_path = os.path.join(output_dir, "analysis_results.json")
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Results exported to {output_path}")
                return output_path
                
            else:
                raise ValueError(f"Unsupported export format: {output_format}")
                
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ""
    
    def get_function_analysis(self, function_name: str) -> Dict[str, Any]:
        """获取指定函数的详细分析结果"""
        if function_name not in self.results['cfgs']:
            return {}
        
        analysis = {
            'cfg': self.results['cfgs'][function_name],
            'pdg': self.results['pdgs'].get(function_name),
            'coupling': None,
            'metrics': {}
        }
        
        # 添加耦合度信息
        coupling_result = self.results.get('coupling', {})
        if coupling_result.get('metrics'):
            analysis['coupling'] = coupling_result['metrics'].get(function_name)
        
        # 添加调用图指标
        if self.call_graph_builder:
            analysis['metrics'] = self.call_graph_builder.compute_function_metrics(function_name)
        
        return analysis
    
    def print_summary(self):
        """打印分析摘要"""
        print("=" * 60)
        print("C STATIC ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"Source File: {self.source_file}")
        print(f"Functions Analyzed: {len(self.results['cfgs'])}")
        
        if self.results['cfgs']:
            total_blocks = sum(cfg.number_of_nodes() for cfg in self.results['cfgs'].values())
            print(f"Total Basic Blocks: {total_blocks}")
        
        if self.results['call_graph']:
            print(f"Function Calls: {self.results['call_graph'].number_of_edges()}")
        
        coupling_result = self.results.get('coupling', {})
        if coupling_result.get('statistics'):
            stats = coupling_result['statistics']
            print(f"Average Coupling: {stats.get('avg_coupling', 0):.2f}")
            print(f"Maximum Coupling: {stats.get('max_coupling', 0):.2f}")
        
        print("=" * 60)


def main():
    """命令行入口点"""
    import argparse
    
    parser = argparse.ArgumentParser(description='C Language Static Analyzer')
    parser.add_argument('source_file', help='C source file to analyze')
    parser.add_argument('-I', '--include', action='append', dest='include_paths',
                       help='Include directories')
    parser.add_argument('--no-visualize', action='store_true',
                       help='Skip visualization generation')
    parser.add_argument('--export-format', choices=['json'], default='json',
                       help='Export format for results')
    parser.add_argument('--output-dir', default='analysis_output',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    try:
        # 创建分析器
        analyzer = CStaticAnalyzer(args.source_file, args.include_paths)
        
        # 执行分析
        print("Starting static analysis...")
        results = analyzer.analyze()
        
        # 生成可视化
        if not args.no_visualize:
            print("Generating visualizations...")
            visualizations = analyzer.visualize_graphs()
        
        # 生成报告
        print("Generating HTML report...")
        report = analyzer.generate_report()
        
        # 导出结果
        print(f"Exporting results in {args.export_format} format...")
        export_path = analyzer.export_results(args.export_format)
        
        # 打印摘要
        analyzer.print_summary()
        
        print(f"\nAnalysis completed successfully!")
        print(f"Results saved to: {args.output_dir}")
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()