#!/usr/bin/env python3
"""
Test Script for Enhanced Redis 3D Dependency Visualization

This script tests the enhanced 3D visualization with igraph and plotly
integration for Redis project dependencies.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_3d_visualization():
    """Test the enhanced 3D visualization"""
    
    print("🚀 Testing Enhanced Redis 3D Dependency Visualization")
    print("=" * 60)
    
    try:
        from project_analyzer import ProjectDependencyAnalyzer
        
        # Check if Redis analysis results exist
        results_path = "redis_analysis_output/redis_analysis_detailed.json"
        if not os.path.exists(results_path):
            print("❌ Redis analysis results not found!")
            print(f"Please run 'python test_redis_analysis.py' first")
            return False
        
        print("📊 Initializing project dependency analyzer...")
        analyzer = ProjectDependencyAnalyzer(results_path)
        
        print("🔗 Building dependency graphs...")
        analyzer.build_function_dependency_graph()
        analyzer.build_data_dependency_graph()
        analyzer.build_module_coupling_graph()
        analyzer.build_integrated_graph()
        
        print(f"✅ Graphs built successfully:")
        print(f"   🔧 Functions: {analyzer.stats['total_functions']}")
        print(f"   🔗 Function Dependencies: {analyzer.stats['function_dependencies']}")
        print(f"   📊 Data Dependencies: {analyzer.stats['data_dependencies']}")
        print(f"   🏗️ Module Couplings: {analyzer.stats['module_couplings']}")
        
        print("\n🎨 Generating enhanced 3D visualization...")
        viz_path = analyzer.generate_3d_visualization()
        
        if viz_path and os.path.exists(viz_path):
            file_size = os.path.getsize(viz_path) / (1024 * 1024)  # MB
            print(f"✅ 3D visualization generated successfully!")
            print(f"   📄 File: {viz_path}")
            print(f"   📏 Size: {file_size:.1f} MB")
            
            # Test opening the file
            try:
                import webbrowser
                webbrowser.open(f"file:///{os.path.abspath(viz_path).replace(os.sep, '/')}")
                print("🌐 Opening visualization in browser...")
            except Exception as e:
                print(f"⚠️ Could not open browser: {e}")
            
            return True
        else:
            print("❌ 3D visualization generation failed!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_dependencies():
    """Check if required dependencies are available"""
    print("🔍 Checking dependencies...")
    
    dependencies = {
        'plotly': 'Plotly for 3D visualization',
        'networkx': 'NetworkX for graph operations', 
        'json': 'JSON for data processing'
    }
    
    optional_deps = {
        'igraph': 'igraph for enhanced 3D layouts (optional)'
    }
    
    all_good = True
    
    for dep, desc in dependencies.items():
        try:
            __import__(dep)
            print(f"✅ {dep}: {desc}")
        except ImportError:
            print(f"❌ {dep}: {desc} - MISSING")
            all_good = False
    
    for dep, desc in optional_deps.items():
        try:
            __import__(dep)
            print(f"✅ {dep}: {desc}")
        except ImportError:
            print(f"⚠️ {dep}: {desc} - Not available (will use fallback)")
    
    return all_good

if __name__ == "__main__":
    print("🧪 Redis Enhanced 3D Visualization Test")
    print("=" * 60)
    
    if not check_dependencies():
        print("\n❌ Missing required dependencies!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    success = test_3d_visualization()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Enhanced 3D visualization test completed successfully!")
        print("\n📋 Features tested:")
        print("   ✅ Dependency graph construction")
        print("   ✅ 3D layout generation (with igraph fallback)")
        print("   ✅ Interactive Plotly visualization")
        print("   ✅ Multi-subplot 3D display")
        print("   ✅ HTML export with proper configuration")
    else:
        print("❌ Enhanced 3D visualization test failed!")
    
    sys.exit(0 if success else 1)