#!/usr/bin/env python3
"""
Redis Project Dependency Analysis - Main Script

This script extends the existing Redis analysis to generate comprehensive 
project-level dependency graphs showing function dependencies and data 
dependencies across the entire Redis codebase.

Usage:
    python redis_project_analysis.py
"""

import sys
import os
from pathlib import Path

# Add source path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from project_analyzer import ProjectDependencyAnalyzer
    import json
    import time
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

def main():
    """Main entry point for Redis project dependency analysis"""
    
    print("🚀 Redis Project Dependency Analysis")
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
        
        # Run complete analysis
        print("🔍 Analyzing project dependencies...")
        results = analyzer.analyze_project()
        
        # Display results
        elapsed_time = time.time() - start_time
        
        print("\n" + "=" * 60)
        print("🎉 Project Dependency Analysis Complete!")
        print("=" * 60)
        print(f"⏱️  Analysis Time: {elapsed_time:.1f} seconds")
        print(f"🔧 Total Functions: {results['statistics']['total_functions']}")
        print(f"🔗 Function Dependencies: {results['statistics']['function_dependencies']}")
        print(f"📊 Data Dependencies: {results['statistics']['data_dependencies']}")
        print(f"🏗️  Module Couplings: {results['statistics']['module_couplings']}")
        print(f"⚠️  Circular Dependencies: {results['statistics']['circular_dependencies']}")
        print()
        print(f"📄 Generated Reports:")
        print(f"  📋 HTML Report: {results['html_report']}")
        print(f"  🎨 Enhanced 3D Visualization: {results['visualization']} ({os.path.getsize(results['visualization']) / (1024*1024):.1f} MB)")
        print(f"  📊 Graph Data Files: project_dependency_output/")
        print(f"  🔬 Static Visualizations: {len(results.get('static_visualizations', {}))} files")
        
        # Try to open the HTML report
        try:
            import webbrowser
            webbrowser.open(f"file:///{os.path.abspath(results['html_report']).replace(os.sep, '/')}")
            print("🌐 Opening HTML report in browser...")
        except Exception:
            pass
        
        return True
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"❌ Analysis failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)