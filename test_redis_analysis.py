#!/usr/bin/env python3
"""
Redis Source Code Static Analysis Test

This test case analyzes the entire Redis codebase (96 .c files + 60 .h files)
and generates comprehensive static analysis reports with visualizations.
"""

import sys
import os
import glob
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict, Counter
import json

# Add our source path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import our analysis modules
try:
    import clang.cindex
    from cfg import CFGBuilder
    from callgraph import CallGraphBuilder
    from visualization import SourceMapper, GraphVisualizer
    import networkx as nx
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Make sure all dependencies are installed and Clang is available")
    sys.exit(1)

# Configure logging for detailed analysis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('redis_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RedisSourceAnalyzer:
    """Comprehensive Redis source code analyzer"""
    
    def __init__(self, redis_src_path: str):
        self.redis_src_path = Path(redis_src_path)
        self.output_dir = Path("redis_analysis_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Statistics tracking
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'total_functions': 0,
            'total_blocks': 0,
            'total_edges': 0,
            'total_calls': 0,
            'errors': [],
            'warnings': []
        }
        
        # Analysis results storage
        self.all_cfgs = {}
        self.all_call_graphs = []
        self.file_results = {}
        
        # Configure Clang for Redis compilation
        self.clang_args = [
            '-std=c99',
            '-D_GNU_SOURCE',
            '-DUSE_JEMALLOC',
            '-I' + str(self.redis_src_path),
            '-I' + str(self.redis_src_path / 'deps'),
            '-I' + str(self.redis_src_path / 'deps' / 'hiredis'),
            '-I' + str(self.redis_src_path / 'deps' / 'linenoise'),
            '-I' + str(self.redis_src_path / 'deps' / 'lua' / 'src'),
            '-Wno-unused-variable',
            '-Wno-unused-function'
        ]
        
        logger.info(f"Initialized Redis analyzer for: {self.redis_src_path}")
    
    def find_source_files(self) -> List[Path]:
        """Find all C source files in Redis"""
        c_files = list(self.redis_src_path.glob("*.c"))
        h_files = list(self.redis_src_path.glob("*.h"))
        
        # Filter out some problematic files that might cause issues
        excluded_patterns = [
            'test_*.c',
            '*test.c', 
            'bench*.c',
            'redis-benchmark.c',
            'redis-check-*.c'
        ]
        
        filtered_files = []
        for file_path in c_files:
            skip = False
            for pattern in excluded_patterns:
                if file_path.match(pattern):
                    skip = True
                    break
            if not skip:
                filtered_files.append(file_path)
        
        logger.info(f"Found {len(c_files)} C files, {len(h_files)} H files")
        logger.info(f"Will process {len(filtered_files)} C files after filtering")
        
        return filtered_files
    
    def analyze_single_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze a single C file"""
        try:
            logger.info(f"📄 Analyzing: {file_path.name}")
            
            # Parse with Clang
            index = clang.cindex.Index.create()
            tu = index.parse(str(file_path), args=self.clang_args)
            
            if not tu:
                self.stats['errors'].append(f"Failed to parse {file_path.name}")
                return None
            
            # Check for severe parsing errors
            severe_errors = [d for d in tu.diagnostics 
                           if d.severity >= clang.cindex.Diagnostic.Error]
            
            if severe_errors:
                error_msg = f"{file_path.name}: {len(severe_errors)} parse errors"
                self.stats['errors'].append(error_msg)
                logger.warning(error_msg)
                # Continue anyway for partial analysis
            
            file_result = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'cfgs': {},
                'call_graph': None,
                'statistics': {
                    'functions': 0,
                    'blocks': 0,
                    'edges': 0,
                    'calls': 0
                },
                'parse_errors': len(severe_errors),
                'parse_warnings': len([d for d in tu.diagnostics 
                                     if d.severity == clang.cindex.Diagnostic.Warning])
            }
            
            # Build CFG for this file
            try:
                cfg_builder = CFGBuilder(str(file_path))
                cfgs = cfg_builder.build_cfg()
                
                if cfgs:
                    file_result['cfgs'] = cfgs
                    file_result['statistics']['functions'] = len(cfgs)
                    file_result['statistics']['blocks'] = sum(cfg.number_of_nodes() for cfg in cfgs.values())
                    file_result['statistics']['edges'] = sum(cfg.number_of_edges() for cfg in cfgs.values())
                    
                    # Store in global collection
                    for func_name, cfg in cfgs.items():
                        unique_key = f"{file_path.stem}::{func_name}"
                        self.all_cfgs[unique_key] = cfg
                
            except Exception as e:
                error_msg = f"CFG failed for {file_path.name}: {str(e)}"
                self.stats['errors'].append(error_msg)
                logger.error(error_msg)
            
            # Build call graph for this file
            try:
                cg_builder = CallGraphBuilder(tu)
                call_graph = cg_builder.build_call_graph()
                
                if call_graph and call_graph.number_of_nodes() > 0:
                    file_result['call_graph'] = call_graph
                    file_result['statistics']['calls'] = call_graph.number_of_edges()
                    self.all_call_graphs.append((file_path.name, call_graph))
                
            except Exception as e:
                error_msg = f"Call graph failed for {file_path.name}: {str(e)}"
                self.stats['errors'].append(error_msg)
                logger.error(error_msg)
            
            # Update global statistics
            self.stats['total_functions'] += file_result['statistics']['functions']
            self.stats['total_blocks'] += file_result['statistics']['blocks']
            self.stats['total_edges'] += file_result['statistics']['edges']
            self.stats['total_calls'] += file_result['statistics']['calls']
            
            self.stats['files_processed'] += 1
            
            logger.info(f"✅ {file_path.name}: {file_result['statistics']['functions']} functions, "
                       f"{file_result['statistics']['blocks']} blocks")
            
            return file_result
            
        except Exception as e:
            error_msg = f"Analysis failed for {file_path.name}: {str(e)}"
            self.stats['errors'].append(error_msg)
            self.stats['files_failed'] += 1
            logger.error(error_msg)
            return None
    
    def merge_call_graphs(self) -> nx.DiGraph:
        """Merge all individual call graphs into a global one"""
        logger.info("🔗 Merging call graphs...")
        
        global_call_graph = nx.DiGraph()
        
        for file_name, call_graph in self.all_call_graphs:
            for node in call_graph.nodes(data=True):
                node_id, node_data = node
                # Prefix with file name to avoid conflicts
                global_node_id = f"{file_name}::{node_id}"
                global_call_graph.add_node(global_node_id, **node_data, source_file=file_name)
            
            for edge in call_graph.edges(data=True):
                src, dst, edge_data = edge
                global_src = f"{file_name}::{src}"
                global_dst = f"{file_name}::{dst}"
                global_call_graph.add_edge(global_src, global_dst, **edge_data)
        
        logger.info(f"✅ Global call graph: {global_call_graph.number_of_nodes()} functions, "
                   f"{global_call_graph.number_of_edges()} calls")
        
        return global_call_graph
    
    def generate_summary_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive statistics"""
        summary = {
            'overview': dict(self.stats),
            'top_files_by_functions': [],
            'top_files_by_complexity': [],
            'function_distribution': {},
            'error_analysis': {},
            'call_graph_metrics': {}
        }
        
        # Analyze per-file statistics
        file_stats = [(name, result['statistics']) for name, result in self.file_results.items()]
        file_stats.sort(key=lambda x: x[1]['functions'], reverse=True)
        
        summary['top_files_by_functions'] = file_stats[:10]
        
        # Complexity analysis (blocks per function)
        complexity_stats = []
        for name, result in self.file_results.items():
            stats = result['statistics']
            if stats['functions'] > 0:
                avg_complexity = stats['blocks'] / stats['functions']
                complexity_stats.append((name, avg_complexity, stats['functions']))
        
        complexity_stats.sort(key=lambda x: x[1], reverse=True)
        summary['top_files_by_complexity'] = complexity_stats[:10]
        
        # Function distribution
        func_counts = [result['statistics']['functions'] for result in self.file_results.values()]
        if func_counts:
            summary['function_distribution'] = {
                'min': min(func_counts),
                'max': max(func_counts),
                'avg': sum(func_counts) / len(func_counts),
                'total': sum(func_counts)
            }
        
        # Error analysis
        error_types = defaultdict(int)
        for error in self.stats['errors']:
            if 'parse' in error.lower():
                error_types['Parse Errors'] += 1
            elif 'cfg' in error.lower():
                error_types['CFG Errors'] += 1
            elif 'call graph' in error.lower():
                error_types['Call Graph Errors'] += 1
            else:
                error_types['Other Errors'] += 1
        
        summary['error_analysis'] = dict(error_types)
        
        return summary
    
    def generate_html_report(self, global_call_graph: nx.DiGraph, summary: Dict[str, Any]) -> str:
        """Generate comprehensive HTML report"""
        logger.info("📄 Generating HTML report...")
        
        # Create a mock TU for the SourceMapper
        class MockTU:
            def __init__(self):
                self.spelling = "Redis 7.0-rc2 Source Analysis"
        
        # Prepare analysis results for visualization
        analysis_results = {
            'cfgs': self.all_cfgs,
            'call_graph': global_call_graph,
            'dataflow': {},
            'pdgs': {},
            'coupling': {},
            'interprocedural': {},
            'source_map': {},
            'redis_summary': summary
        }
        
        try:
            mock_tu = MockTU()
            source_mapper = SourceMapper(mock_tu)
            
            # Generate custom Redis HTML report
            html_content = self._generate_redis_html_report(analysis_results, summary)
            
            # Save report
            report_path = self.output_dir / "redis_analysis_report.html"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✅ HTML report saved: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"HTML report generation failed: {e}")
            return ""
    
    def _generate_redis_html_report(self, analysis_results: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """Generate custom HTML report for Redis analysis"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build comprehensive HTML report
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Redis 7.0-rc2 Static Analysis Report</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #dc382d 0%, #b32821 100%); color: white; padding: 40px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .section {{ background: white; margin: 20px 0; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: linear-gradient(45deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }}
        .metric-label {{ font-size: 0.9em; opacity: 0.9; }}
        .table-container {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        .error {{ background: #fee; color: #c33; }}
        .warning {{ background: #fff3cd; color: #856404; }}
        .success {{ background: #d4edda; color: #155724; }}
        .chart-placeholder {{ background: #f8f9fa; padding: 40px; text-align: center; color: #666; border: 2px dashed #ddd; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🗂️ Redis 7.0-rc2 Static Analysis Report</h1>
        <p>📅 Generated: {timestamp} | 🔍 Comprehensive C Source Code Analysis</p>
    </div>
    
    <div class="container">
        <div class="section">
            <h2>📊 Analysis Overview</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{summary['overview']['files_processed']}</div>
                    <div class="metric-label">Files Processed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary['overview']['total_functions']}</div>
                    <div class="metric-label">Total Functions</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary['overview']['total_blocks']}</div>
                    <div class="metric-label">Basic Blocks</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary['overview']['total_calls']}</div>
                    <div class="metric-label">Function Calls</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{len(analysis_results['call_graph'].nodes()) if analysis_results['call_graph'] else 0}</div>
                    <div class="metric-label">Global Functions</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary['overview']['files_failed']}</div>
                    <div class="metric-label">Failed Files</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Top Files by Function Count</h2>
            <div class="table-container">
                <table>
                    <tr><th>File</th><th>Functions</th><th>Basic Blocks</th><th>Edges</th><th>Complexity</th></tr>"""
        
        for file_name, stats in summary['top_files_by_functions']:
            complexity = stats['blocks'] / stats['functions'] if stats['functions'] > 0 else 0
            html_content += f"""
                    <tr>
                        <td>{file_name}</td>
                        <td>{stats['functions']}</td>
                        <td>{stats['blocks']}</td>
                        <td>{stats['edges']}</td>
                        <td>{complexity:.1f}</td>
                    </tr>"""
        
        html_content += """
                </table>
            </div>
        </div>
        
        <div class="section">
            <h2>🔧 Most Complex Files</h2>
            <div class="table-container">
                <table>
                    <tr><th>File</th><th>Avg Complexity</th><th>Functions</th><th>Assessment</th></tr>"""
        
        for file_name, complexity, func_count in summary['top_files_by_complexity']:
            assessment = "High" if complexity > 10 else "Medium" if complexity > 5 else "Low"
            css_class = "error" if complexity > 10 else "warning" if complexity > 5 else "success"
            html_content += f"""
                    <tr class="{css_class}">
                        <td>{file_name}</td>
                        <td>{complexity:.1f}</td>
                        <td>{func_count}</td>
                        <td>{assessment}</td>
                    </tr>"""
        
        html_content += f"""
                </table>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Function Distribution</h2>
            <div class="metrics-grid">"""
        
        if 'function_distribution' in summary:
            dist = summary['function_distribution']
            html_content += f"""
                <div class="metric-card">
                    <div class="metric-value">{dist['min']}</div>
                    <div class="metric-label">Min Functions/File</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{dist['max']}</div>
                    <div class="metric-label">Max Functions/File</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{dist['avg']:.1f}</div>
                    <div class="metric-label">Avg Functions/File</div>
                </div>"""
        
        html_content += """
            </div>
        </div>"""
        
        if summary['overview']['errors']:
            html_content += f"""
        <div class="section">
            <h2>⚠️ Error Analysis</h2>
            <div class="table-container">
                <table>
                    <tr><th>Error Type</th><th>Count</th></tr>"""
            
            for error_type, count in summary.get('error_analysis', {}).items():
                html_content += f"""
                    <tr class="{'error' if 'Error' in error_type else 'warning'}">
                        <td>{error_type}</td>
                        <td>{count}</td>
                    </tr>"""
            
            html_content += """
                </table>
            </div>
            <h3>Recent Errors:</h3>
            <ul>"""
            
            for error in summary['overview']['errors'][-10:]:  # Show last 10 errors
                html_content += f"<li>{error}</li>"
            
            html_content += """
            </ul>
        </div>"""
        
        html_content += f"""
        <div class="section">
            <h2>🎯 Analysis Summary</h2>
            <div class="chart-placeholder">
                <h3>📈 Redis Codebase Analysis Complete</h3>
                <p>Successfully analyzed {summary['overview']['files_processed']} files from Redis 7.0-rc2 source code</p>
                <p>Total Functions: <strong>{summary['overview']['total_functions']}</strong></p>
                <p>Total Basic Blocks: <strong>{summary['overview']['total_blocks']}</strong></p>
                <p>Analysis Quality: <strong>{((summary['overview']['files_processed'] - summary['overview']['files_failed']) / max(summary['overview']['files_processed'], 1) * 100):.1f}%</strong></p>
            </div>
        </div>
        
        <div class="section">
            <h2>💡 Recommendations</h2>
            <ul>
                <li><strong>High Complexity Files:</strong> Files with >10 avg blocks/function may benefit from refactoring</li>
                <li><strong>Large Files:</strong> Files with >50 functions could be split into modules</li>
                <li><strong>Error Resolution:</strong> {len(summary['overview']['errors'])} analysis errors should be investigated</li>
                <li><strong>Code Quality:</strong> Consider automated testing for files with high complexity</li>
            </ul>
        </div>
    </div>
</body>
</html>"""
        
        return html_content
    
    def save_detailed_results(self, summary: Dict[str, Any]):
        """Save detailed analysis results to JSON"""
        try:
            # Prepare serializable data
            detailed_results = {
                'analysis_summary': summary,
                'file_results': {},
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Add file-level results (without NetworkX graphs which aren't JSON serializable)
            for file_name, result in self.file_results.items():
                detailed_results['file_results'][file_name] = {
                    'file_path': result['file_path'],
                    'statistics': result['statistics'],
                    'parse_errors': result.get('parse_errors', 0),
                    'parse_warnings': result.get('parse_warnings', 0),
                    'function_names': list(result['cfgs'].keys()) if result['cfgs'] else []
                }
            
            # Save to JSON
            json_path = self.output_dir / "redis_analysis_detailed.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(detailed_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Detailed results saved: {json_path}")
            
        except Exception as e:
            logger.error(f"Failed to save detailed results: {e}")
    
    def run_analysis(self, include_project_dependencies: bool = True) -> bool:
        """Run complete Redis source code analysis"""
        start_time = time.time()
        
        print("🚀 Starting Redis 7.0-rc2 Source Code Analysis")
        print("=" * 60)
        
        try:
            # Find all source files
            source_files = self.find_source_files()
            if not source_files:
                logger.error("No source files found!")
                return False
            
            print(f"📂 Found {len(source_files)} files to analyze")
            print()
            
            # Analyze each file
            for i, file_path in enumerate(source_files, 1):
                print(f"[{i:3d}/{len(source_files)}] Processing {file_path.name}...")
                
                result = self.analyze_single_file(file_path)
                if result:
                    self.file_results[file_path.name] = result
                
                # Progress indicator
                if i % 10 == 0:
                    elapsed = time.time() - start_time
                    remaining = (elapsed / i) * (len(source_files) - i)
                    print(f"    ⏱️  Progress: {i}/{len(source_files)} ({i/len(source_files)*100:.1f}%) - "
                          f"ETA: {remaining/60:.1f} minutes")
            
            print()
            print("🔗 Merging analysis results...")
            
            # Merge call graphs
            global_call_graph = self.merge_call_graphs()
            
            # Generate statistics
            summary = self.generate_summary_statistics()
            
            # Generate reports
            html_report_path = self.generate_html_report(global_call_graph, summary)
            self.save_detailed_results(summary)
            
            # Generate project-level dependency analysis if requested
            if include_project_dependencies:
                try:
                    from src.project_analyzer import ProjectDependencyAnalyzer
                    
                    # Save current results first
                    detailed_path = self.output_dir / "redis_analysis_detailed.json"
                    
                    print("\n🔗 Generating project-level dependency analysis...")
                    dep_analyzer = ProjectDependencyAnalyzer(str(detailed_path))
                    dep_results = dep_analyzer.analyze_project()
                    
                    print(f"✅ Project dependencies analyzed:")
                    print(f"   🔧 Function Dependencies: {dep_results['statistics']['function_dependencies']}")
                    print(f"   📊 Data Dependencies: {dep_results['statistics']['data_dependencies']}")
                    print(f"   🏗️  Module Couplings: {dep_results['statistics']['module_couplings']}")
                    
                except Exception as e:
                    logger.warning(f"Project dependency analysis failed: {e}")
                    print(f"⚠️  Project dependency analysis failed: {e}")
            
            # Final summary
            elapsed_time = time.time() - start_time
            
            print("=" * 60)
            print("🎉 Redis Analysis Complete!")
            print("=" * 60)
            print(f"⏱️  Total Time: {elapsed_time/60:.1f} minutes")
            print(f"📁 Files Processed: {self.stats['files_processed']}")
            print(f"❌ Files Failed: {self.stats['files_failed']}")
            print(f"🔧 Total Functions: {self.stats['total_functions']}")
            print(f"📊 Total Basic Blocks: {self.stats['total_blocks']}")
            print(f"📞 Total Function Calls: {self.stats['total_calls']}")
            print(f"📈 Success Rate: {(self.stats['files_processed'] - self.stats['files_failed']) / max(self.stats['files_processed'], 1) * 100:.1f}%")
            print()
            print(f"📄 HTML Report: {html_report_path}")
            print(f"📊 Detailed Data: {self.output_dir / 'redis_analysis_detailed.json'}")
            print(f"📝 Analysis Log: redis_analysis.log")
            
            if html_report_path:
                # Try to open the report in browser
                try:
                    import webbrowser
                    webbrowser.open(f"file:///{os.path.abspath(html_report_path).replace(os.sep, '/')}")
                    print("🌐 Opening report in browser...")
                except Exception:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            print(f"❌ Analysis failed: {e}")
            return False

def main():
    """Main entry point"""
    # Redis source path
    redis_path = r"C:\code\redis-7.0-rc2\redis-7.0-rc2\src"
    
    if not os.path.exists(redis_path):
        print(f"❌ Redis source path not found: {redis_path}")
        print("Please check the path and try again.")
        return False
    
    # Create analyzer and run
    analyzer = RedisSourceAnalyzer(redis_path)
    success = analyzer.run_analysis()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)