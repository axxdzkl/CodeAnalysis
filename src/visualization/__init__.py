"""
Visualization module - Simple HTML report generation
"""

import networkx as nx
from typing import Dict, Any, Optional, List, Tuple, Set
import logging
import os
from datetime import datetime
import math

# Setup logger
logger = logging.getLogger(__name__)

class AdvancedGraphVisualizer:
    """Advanced graph visualizer for code analysis results"""
    
    def __init__(self):
        self.output_dir = "analysis_output"
        os.makedirs(self.output_dir, exist_ok=True)

class SourceMapper:
    """Source code mapper for generating analysis reports"""
    
    def __init__(self, tu):
        self.tu = tu
        self.source_map = {}
    
    def build_source_map(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Build source mapping"""
        logger.info("Building source map...")
        return self.source_map
        
    def generate_html_report(self, analysis_results: Dict[str, Any]) -> str:
        """Generate HTML report"""
        return self.generate_enhanced_html_report(analysis_results)
        
    def generate_enhanced_html_report(self, analysis_results: Dict[str, Any]) -> str:
        """Generate enhanced HTML report"""
        logger.info("Generating enhanced HTML report...")
        
        # Generate content first
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        source_file = getattr(self.tu, 'spelling', 'Unknown')
        
        overview_metrics = self._generate_overview_metrics(analysis_results)
        call_graph_stats = self._generate_call_graph_stats(analysis_results)
        coupling_analysis = self._generate_coupling_analysis(analysis_results)
        dataflow_results = self._generate_dataflow_results(analysis_results)
        pdg_stats = self._generate_pdg_stats(analysis_results)
        optimization_suggestions = self._generate_optimization_suggestions(analysis_results)
        
        # Build HTML report with simple inline styles
        html_content = (
            '<!DOCTYPE html>\n'
            '<html>\n'
            '<head>\n'
            '<title>C Static Analysis Report</title>\n'
            '<meta charset="utf-8">\n'
            '<style>\n'
            'body { font-family: Arial, sans-serif; margin: 20px; }\n'
            '.header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }\n'
            '.section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }\n'
            '.metrics { display: flex; flex-wrap: wrap; gap: 20px; }\n'
            '.metric-card { background: #f9f9f9; padding: 15px; border-radius: 5px; min-width: 200px; }\n'
            '.metric-value { font-size: 24px; font-weight: bold; color: #2196F3; }\n'
            '.metric-label { color: #666; }\n'
            'table { border-collapse: collapse; width: 100%; margin: 10px 0; }\n'
            'th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n'
            'th { background-color: #f2f2f2; }\n'
            '</style>\n'
            '</head>\n'
            '<body>\n'
            '<div class="header">\n'
            '<h1>C Language Static Analysis Report</h1>\n'
            f'<p>Generated: {timestamp}</p>\n'
            f'<p>Source file: {source_file}</p>\n'
            '</div>\n'
            '<div class="section">\n'
            '<h2>Analysis Overview</h2>\n'
            '<div class="metrics">\n'
            f'{overview_metrics}\n'
            '</div>\n'
            '</div>\n'
            '<div class="section">\n'
            '<h2>Function Call Graph Statistics</h2>\n'
            f'{call_graph_stats}\n'
            '</div>\n'
            '<div class="section">\n'
            '<h2>Coupling Analysis</h2>\n'
            f'{coupling_analysis}\n'
            '</div>\n'
            '<div class="section">\n'
            '<h2>Data Flow Analysis Results</h2>\n'
            f'{dataflow_results}\n'
            '</div>\n'
            '<div class="section">\n'
            '<h2>Program Dependence Graph Statistics</h2>\n'
            f'{pdg_stats}\n'
            '</div>\n'
            '<div class="section">\n'
            '<h2>Optimization Suggestions</h2>\n'
            f'{optimization_suggestions}\n'
            '</div>\n'
            '</body>\n'
            '</html>'
        )
        
        # Convert escape sequences to actual newlines
        html_content = html_content.replace('\\n', '\n')
        
        return html_content
    
    def _generate_overview_metrics(self, analysis_results: Dict[str, Any]) -> str:
        """Generate overview metrics HTML"""
        cfgs = analysis_results.get('cfgs', {})
        call_graph = analysis_results.get('call_graph')
        
        total_functions = len(cfgs)
        total_blocks = sum(cfg.number_of_nodes() for cfg in cfgs.values())
        total_calls = call_graph.number_of_edges() if call_graph else 0
        
        return (
            '<div class="metric-card">'
            f'<div class="metric-value">{total_functions}</div>'
            '<div class="metric-label">Total Functions</div>'
            '</div>'
            '<div class="metric-card">'
            f'<div class="metric-value">{total_blocks}</div>'
            '<div class="metric-label">Basic Blocks</div>'
            '</div>'
            '<div class="metric-card">'
            f'<div class="metric-value">{total_calls}</div>'
            '<div class="metric-label">Function Calls</div>'
            '</div>'
        )
    
    def _generate_call_graph_stats(self, analysis_results: Dict[str, Any]) -> str:
        """Generate call graph statistics HTML"""
        call_graph = analysis_results.get('call_graph')
        if not call_graph:
            return "<p>No call graph generated</p>"
        
        return (
            f"<p>Function nodes: {call_graph.number_of_nodes()}</p>"
            f"<p>Call relationships: {call_graph.number_of_edges()}</p>"
        )
    
    def _generate_coupling_analysis(self, analysis_results: Dict[str, Any]) -> str:
        """Generate coupling analysis HTML"""
        coupling = analysis_results.get('coupling', {})
        if not coupling:
            return "<p>No coupling information calculated</p>"
        
        return "<p>Coupling analysis completed</p>"
    
    def _generate_dataflow_results(self, analysis_results: Dict[str, Any]) -> str:
        """Generate data flow analysis results HTML"""
        dataflow = analysis_results.get('dataflow', {})
        if not dataflow:
            return "<p>No data flow analysis performed</p>"
        
        return "<p>Data flow analysis completed</p>"
    
    def _generate_pdg_stats(self, analysis_results: Dict[str, Any]) -> str:
        """Generate PDG statistics HTML"""
        pdgs = analysis_results.get('pdgs', {})
        total_pdg_nodes = sum(pdg.number_of_nodes() for pdg in pdgs.values()) if pdgs else 0
        
        return (
            f"<p>Total PDG nodes: {total_pdg_nodes}</p>"
            f"<p>Number of PDGs: {len(pdgs)}</p>"
        )
    
    def _generate_optimization_suggestions(self, analysis_results: Dict[str, Any]) -> str:
        """Generate optimization suggestions HTML"""
        return (
            "<ul>"
            "<li>Consider refactoring highly coupled functions</li>"
            "<li>Optimize complex control flows</li>"
            "<li>Reduce usage of global variables</li>"
            "</ul>"
        )

# Legacy compatibility alias
GraphVisualizer = AdvancedGraphVisualizer

# Export main classes
__all__ = ['AdvancedGraphVisualizer', 'SourceMapper', 'GraphVisualizer']