#!/usr/bin/env python3
"""
Generate Separate 3D Visualizations - Create individual HTML files for each graph type
"""

import sys
import os
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

def generate_separate_visualizations():
    """Generate separate HTML files for each graph type"""
    
    print("🎨 Generating Separate 3D Visualizations")
    print("=" * 60)
    
    # Check if Redis analysis results exist
    results_path = "redis_analysis_output/redis_analysis_detailed.json"
    if not os.path.exists(results_path):
        print("❌ Redis analysis results not found!")
        print(f"Please run 'python test_redis_analysis.py' first to generate {results_path}")
        return False
    
    start_time = time.time()
    
    try:
        # Initialize project analyzer
        print("📊 Initializing project dependency analyzer...")
        analyzer = ProjectDependencyAnalyzer(results_path)
        
        # Build all dependency graphs
        print("🔗 Building enhanced dependency graphs...")
        analyzer.build_function_dependency_graph()
        analyzer.build_data_dependency_graph()
        analyzer.build_module_coupling_graph()
        analyzer.build_integrated_graph()
        
        print(f"  Functions: {analyzer.stats['total_functions']}")
        print(f"  Function Dependencies: {analyzer.stats['function_dependencies']}")
        print(f"  Data Dependencies: {analyzer.stats['data_dependencies']}")
        print(f"  Module Couplings: {analyzer.stats['module_couplings']}")
        
        # Generate separate visualizations
        print("🎨 Generating separate 3D visualizations...")
        viz_paths = analyzer._create_separate_3d_visualizations()
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "=" * 60)
        print("🎉 Separate 3D Visualizations Generated!")
        print("=" * 60)
        print(f"⏱️  Generation Time: {elapsed_time:.1f} seconds")
        print()
        
        for graph_type, path in viz_paths.items():
            if os.path.exists(path):
                file_size = os.path.getsize(path) / (1024 * 1024)  # MB
                print(f"📄 {graph_type.replace('_', ' ').title()}: {path}")
                print(f"   Size: {file_size:.1f} MB")
                print()
        
        print("🌐 You can now open each HTML file individually in your browser!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Visualization generation failed: {e}")
        print(f"❌ Visualization generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = generate_separate_visualizations()
    sys.exit(0 if success else 1)