#!/usr/bin/env python3
"""
Test Enhanced Features - Quick test for the improved dependency analysis
"""

import sys
import os
import json
import time
from pathlib import Path

# Add source path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from project_analyzer import ProjectDependencyAnalyzer
    import logging
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_enhanced_dependency_analysis():
    """Test the enhanced dependency analysis features"""
    
    print("🧪 Testing Enhanced Redis Dependency Analysis")
    print("=" * 50)
    
    # Check if Redis analysis results exist
    results_path = "redis_analysis_output/redis_analysis_detailed.json"
    if not os.path.exists(results_path):
        print("❌ Redis analysis results not found!")
        print(f"Please run 'python test_redis_analysis.py' first to generate {results_path}")
        return False
    
    try:
        # Initialize project analyzer
        print("📊 Initializing enhanced project analyzer...")
        analyzer = ProjectDependencyAnalyzer(results_path)
        
        # Test graph building
        print("🔗 Testing enhanced function dependency graph...")
        analyzer.build_function_dependency_graph()
        print(f"  Functions: {analyzer.stats['total_functions']}")
        print(f"  Dependencies: {analyzer.stats['function_dependencies']}")
        
        print("📊 Testing enhanced data dependency graph...")
        analyzer.build_data_dependency_graph()
        print(f"  Data Dependencies: {analyzer.stats['data_dependencies']}")
        
        print("🏗️ Testing module coupling graph...")
        analyzer.build_module_coupling_graph()
        print(f"  Module Couplings: {analyzer.stats['module_couplings']}")
        
        # Test just the function dependencies standalone visualization
        print("🎨 Testing standalone function dependencies visualization...")
        func_fig = analyzer._create_function_dependencies_standalone()
        print(f"  ✅ Function dependencies visualization created successfully")
        
        # Test the helper methods
        print("🔧 Testing enhanced helper methods...")
        
        # Test layout generation
        if analyzer.function_dependency_graph.number_of_nodes() > 0:
            sample_graph = analyzer._sample_graph(analyzer.function_dependency_graph, 50)
            x, y, z = analyzer._get_enhanced_3d_layout(sample_graph, 'function')
            print(f"  ✅ Enhanced 3D layout: {len(x)} coordinates generated")
            
            # Test color generation
            colors, info = analyzer._get_enhanced_node_colors(sample_graph.nodes())
            print(f"  ✅ Enhanced colors: {len(colors)} colors, {info['total_files']} files")
        
        print("🎯 Testing separate HTML generation (lightweight)...")
        
        # Generate just one standalone visualization for testing
        try:
            func_fig = analyzer._create_function_dependencies_standalone()
            test_path = Path("project_dependency_output") / "test_function_deps.html"
            
            import plotly.offline as pyo
            pyo.plot(func_fig, filename=str(test_path), auto_open=False)
            
            file_size = test_path.stat().st_size if test_path.exists() else 0
            print(f"  ✅ Test HTML generated: {file_size / 1024:.1f} KB")
            
        except Exception as e:
            print(f"  ⚠️ HTML generation test failed: {e}")
        
        print()
        print("=" * 50)
        print("🎉 Enhanced Feature Test Results:")
        print(f"  🔧 Total Functions: {analyzer.stats['total_functions']}")
        print(f"  🔗 Function Dependencies: {analyzer.stats['function_dependencies']}")
        print(f"  📊 Data Dependencies: {analyzer.stats['data_dependencies']}")
        print(f"  🏗️ Module Couplings: {analyzer.stats['module_couplings']}")
        print("=" * 50)
        
        # Check if we have more dependencies than before
        if analyzer.stats['function_dependencies'] > 500:
            print("✅ Function dependencies significantly increased - enhancement working!")
        
        if analyzer.stats['data_dependencies'] > 15:
            print("✅ Data dependencies significantly increased - enhancement working!")
        
        return True
        
    except Exception as e:
        logger.error(f"Enhanced test failed: {e}")
        print(f"❌ Enhanced test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_dependency_analysis()
    sys.exit(0 if success else 1)