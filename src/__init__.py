"""
C语言静态分析系统

这是一个基于Python和Clang/AST的工业级C语言静态分析系统，
支持控制流图、数据流分析、程序依赖图、函数调用图等多种分析功能。

主要模块:
- cfg: 控制流图构建
- dataflow: 数据流分析  
- pdg: 程序依赖图构建
- callgraph: 函数调用图构建
- interprocedural: 函数间分析
- coupling: 耦合度计算
- visualization: 可视化输出
- analyzer: 主分析器
"""

__version__ = "1.0.0"
__author__ = "CodeAnalysis Team"
__email__ = "team@codeanalysis.com"

from .analyzer import CStaticAnalyzer

__all__ = ['CStaticAnalyzer']