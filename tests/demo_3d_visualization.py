#!/usr/bin/env python3
"""
3D可视化演示脚本

演示新的Plotly 3D交互式可视化功能
支持大规模代码仓库(>1000节点，>10000条边)的高性能展示
"""

import sys
import os
sys.path.insert(0, 'src')

from src.analyzer import CStaticAnalyzer
from src.visualization import AdvancedGraphVisualizer, SourceMapper
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def demo_3d_visualization():
    """演示3D可视化功能"""
    
    print("🚀 3D交互式可视化演示")
    print("=" * 50)
    
    # 示例文件
    test_files = [
        'examples/simple_example.c',
        'examples/linked_list.c',
        'examples/matrix_operations.c'
    ]
    
    # 创建3D可视化器
    viz = AdvancedGraphVisualizer()
    
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"⚠️ 文件不存在: {test_file}")
            continue
            
        print(f"\n📁 分析文件: {test_file}")
        
        try:
            # 分析代码
            analyzer = CStaticAnalyzer(test_file)
            results = analyzer.analyze()
            
            # 获取分析结果
            cfgs = results.get('cfgs', {})
            call_graph = results.get('call_graph')
            coupling_data = results.get('coupling', {})
            
            print(f"   ✅ 发现 {len(cfgs)} 个函数")
            
            if call_graph:
                print(f"   📞 调用图: {call_graph.number_of_nodes()} 节点, {call_graph.number_of_edges()} 边")
            
            # 生成3D CFG可视化
            if cfgs:
                main_func = 'main' if 'main' in cfgs else next(iter(cfgs.keys()))
                print(f"   🎯 生成3D CFG: {main_func}")
                
                cfg_path = viz.visualize_3d_cfg(cfgs[main_func], main_func)
                if cfg_path:
                    print(f"      💾 保存到: {cfg_path}")
            
            # 生成3D调用图
            if call_graph and call_graph.number_of_nodes() > 1:
                print("   🕸️ 生成3D调用图")
                call_path = viz.visualize_3d_call_graph(call_graph)
                if call_path:
                    print(f"      💾 保存到: {call_path}")
            
            # 生成交互式耦合度热力图
            if coupling_data and coupling_data.get('metrics'):
                print("   🔥 生成交互式耦合度热力图")
                func_names = list(coupling_data['metrics'].keys())
                heatmap_path = viz.visualize_interactive_coupling_heatmap(coupling_data, func_names)
                if heatmap_path:
                    print(f"      💾 保存到: {heatmap_path}")
            
            # 生成增强HTML报告
            print("   📊 生成增强HTML报告")
            try:
                import clang.cindex
                index = clang.cindex.Index.create()
                tu = index.parse(test_file)
                
                mapper = SourceMapper(tu)
                mapper.build_source_map(results)
                
                report_html = mapper.generate_enhanced_html_report(results)
                report_path = f"analysis_output/enhanced_report_{os.path.basename(test_file)}.html"
                
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report_html)
                
                print(f"      💾 保存到: {report_path}")
                
            except Exception as e:
                print(f"      ❌ HTML报告生成失败: {e}")
                
        except Exception as e:
            print(f"   ❌ 分析失败: {e}")
            logger.error(f"Analysis failed for {test_file}: {e}")
    
    print(f"\n🎉 演示完成！")
    print(f"📂 所有文件保存在: analysis_output/")
    print(f"🌐 在浏览器中打开HTML文件查看交互式可视化")

def demo_large_scale_optimization():
    """演示大规模数据优化功能"""
    
    print("\n🏗️ 大规模数据优化演示")
    print("=" * 50)
    
    import networkx as nx
    
    # 创建模拟的大规模图
    print("📊 创建模拟大规模调用图...")
    
    # 生成随机调用图 (模拟1500节点, 12000边)
    G = nx.scale_free_graph(1500, seed=42)
    G = nx.DiGraph(G)  # 转为有向图
    
    # 添加节点属性
    for i, node in enumerate(G.nodes()):
        G.nodes[node]['function_name'] = f'function_{i}'
        G.nodes[node]['is_recursive'] = (i % 20 == 0)  # 5%递归函数
    
    print(f"   ✅ 生成图: {G.number_of_nodes()} 节点, {G.number_of_edges()} 边")
    
    # 测试大规模可视化
    viz = AdvancedGraphVisualizer()
    
    print("🎯 测试大规模优化算法...")
    optimized_graph = viz._optimize_large_graph(G, max_nodes=1000)
    
    print(f"   📉 优化结果: {optimized_graph.number_of_nodes()} 节点, {optimized_graph.number_of_edges()} 边")
    print(f"   📊 压缩率: {optimized_graph.number_of_nodes()/G.number_of_nodes()*100:.1f}%")
    
    # 生成3D可视化
    print("🎨 生成3D交互式可视化...")
    
    try:
        large_viz_path = viz.visualize_3d_call_graph(optimized_graph, highlight_cycles=True)
        if large_viz_path:
            print(f"   💾 大规模3D可视化保存到: {large_viz_path}")
            print(f"   🌟 支持缩放、旋转、悬停交互")
        
    except Exception as e:
        print(f"   ❌ 大规模可视化失败: {e}")
        logger.error(f"Large-scale visualization failed: {e}")

def show_performance_metrics():
    """显示性能指标"""
    
    print("\n⚡ 性能优化特性")
    print("=" * 50)
    
    features = [
        "🎯 智能节点采样: 超过1000节点时自动优化显示",
        "🧠 重要性评分: 基于度数和中介中心性的节点重要性计算", 
        "🔄 动态布局算法: 支持force-directed, hierarchical, random多种布局",
        "📊 层次化展示: DAG自动分层,非DAG智能聚类",
        "🎨 交互式探索: 缩放、旋转、悬停、点击交互",
        "📈 实时性能监控: 自动检测并提示大规模数据处理状态",
        "💾 多格式输出: HTML交互式 + PNG静态图像",
        "🎮 实时仪表板: 集成Dash的实时交互式分析面板"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print(f"\n💡 技术栈升级:")
    print(f"  📦 Plotly: 3D交互式可视化")
    print(f"  🎛️ Dash: 实时Web仪表板") 
    print(f"  🧮 scikit-learn: 图嵌入和聚类")
    print(f"  🐼 pandas: 数据处理和分析")
    print(f"  🔢 numpy: 高性能数值计算")

def main():
    """主函数"""
    
    print("🌟 C语言静态分析系统 - 3D交互式可视化增强版")
    print("🎯 支持>1000节点, >10000条边的大规模代码仓库")
    print("=" * 60)
    
    # 检查依赖
    missing_deps = []
    
    try:
        import plotly
        print("✅ Plotly 已安装")
    except ImportError:
        missing_deps.append("plotly")
    
    try:
        import dash
        print("✅ Dash 已安装")
    except ImportError:
        missing_deps.append("dash")
    
    try:
        import pandas
        print("✅ Pandas 已安装")
    except ImportError:
        missing_deps.append("pandas")
    
    try:
        import sklearn
        print("✅ Scikit-learn 已安装")
    except ImportError:
        missing_deps.append("scikit-learn")
    
    if missing_deps:
        print(f"\n⚠️ 缺少依赖包: {', '.join(missing_deps)}")
        print(f"💡 安装命令: pip install {' '.join(missing_deps)}")
        print(f"📦 或运行: pip install -r requirements.txt")
        return
    
    try:
        # 演示基本3D可视化
        demo_3d_visualization()
        
        # 演示大规模优化
        demo_large_scale_optimization()
        
        # 显示性能特性
        show_performance_metrics()
        
        print(f"\n🎉 所有演示完成!")
        print(f"🌐 打开 analysis_output/ 目录中的HTML文件体验交互式可视化")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ 用户中断演示")
    except Exception as e:
        print(f"\n❌ 演示过程出错: {e}")
        logger.error(f"Demo failed: {e}")

if __name__ == "__main__":
    main()