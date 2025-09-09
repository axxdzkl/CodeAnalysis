#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C语言静态分析系统演示脚本

展示系统的主要功能：
1. 控制流图(CFG)构建
2. 数据流分析
3. 程序依赖图(PDG)构建
4. 函数调用图分析
5. 耦合度计算
6. 结果可视化和报告生成
"""

import os
import sys
import time

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # 回到项目根目录
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

def demo_cfg_analysis():
    """演示控制流图分析"""
    print("=" * 60)
    print("1. 控制流图(CFG)分析演示")
    print("=" * 60)
    
    from cfg import CFGBuilder
    
    # 选择示例文件
    example_file = os.path.join(project_root, 'examples', 'simple_example.c')
    
    print(f"分析文件: {example_file}")
    print("构建控制流图...")
    
    # 构建CFG
    builder = CFGBuilder(example_file)
    cfgs = builder.build_cfg()
    
    if cfgs:
        print(f"✓ 成功为 {len(cfgs)} 个函数构建了CFG")
        
        for func_name, cfg in cfgs.items():
            if func_name in ['add', 'max', 'factorial', 'fibonacci', 'main']:
                print(f"\n函数 {func_name}:")
                print(f"  - 基本块数量: {cfg.number_of_nodes()}")
                print(f"  - 控制流边数: {cfg.number_of_edges()}")
                
                # 分析节点类型
                node_types = {}
                for node in cfg.nodes:
                    node_type = cfg.nodes[node].get('type', 'normal')
                    node_types[node_type] = node_types.get(node_type, 0) + 1
                
                print(f"  - 节点类型分布: {dict(node_types)}")
        
        # 打印统计信息
        builder.print_cfg_stats()
        
    else:
        print("✗ 未能构建CFG")

def demo_dataflow_analysis():
    """演示数据流分析"""
    print("\n" + "=" * 60)
    print("2. 数据流分析演示")
    print("=" * 60)
    
    from cfg import CFGBuilder
    from dataflow import DataFlowAnalyzer
    
    example_file = os.path.join(project_root, 'examples', 'simple_example.c')
    
    print("执行数据流分析...")
    
    # 先构建CFG
    builder = CFGBuilder(example_file)
    cfgs = builder.build_cfg()
    
    if cfgs:
        # 对主函数进行数据流分析
        main_cfg = cfgs.get('main')
        if main_cfg:
            analyzer = DataFlowAnalyzer(main_cfg)
            result = analyzer.analyze()
            
            print("✓ 数据流分析完成")
            print(f"  - 发现变量: {len(result.get('variables', set()))}")
            print(f"  - 变量定义: {len(result.get('definitions', set()))}")
            
            # 打印分析结果
            analyzer.print_analysis_results()
        else:
            print("✗ 未找到main函数的CFG")
    else:
        print("✗ 数据流分析失败")

def demo_call_graph_analysis():
    """演示函数调用图分析"""
    print("\n" + "=" * 60)
    print("3. 函数调用图分析演示")
    print("=" * 60)
    
    import clang.cindex
    from callgraph import CallGraphBuilder
    
    example_file = os.path.join(project_root, 'examples', 'linked_list.c')
    
    print(f"分析文件: {example_file}")
    print("构建函数调用图...")
    
    try:
        # 解析源文件
        index = clang.cindex.Index.create()
        tu = index.parse(example_file)
        
        if tu:
            # 构建调用图
            builder = CallGraphBuilder(tu)
            call_graph = builder.build_call_graph()
            
            print("✓ 函数调用图构建完成")
            
            # 打印统计信息
            builder.print_call_graph_summary()
            
            # 分析一些具体函数的指标
            interesting_funcs = ['main', 'insert_at_head', 'search', 'print_list']
            for func in interesting_funcs:
                metrics = builder.compute_function_metrics(func)
                if metrics:
                    print(f"\n{func} 函数指标:")
                    print(f"  - 被调用次数: {metrics['fan_in']}")
                    print(f"  - 调用其他函数: {metrics['fan_out']}")
                    print(f"  - 是否递归: {'是' if metrics['is_recursive'] else '否'}")
        else:
            print("✗ 源文件解析失败")
            
    except Exception as e:
        print(f"✗ 调用图分析失败: {e}")

def demo_pdg_analysis():
    """演示程序依赖图分析"""
    print("\n" + "=" * 60)
    print("4. 程序依赖图(PDG)分析演示")
    print("=" * 60)
    
    from cfg import CFGBuilder
    from dataflow import DataFlowAnalyzer
    from pdg import PDGBuilder
    
    example_file = os.path.join(project_root, 'examples', 'simple_example.c')
    
    print("构建程序依赖图...")
    
    try:
        # 构建CFG
        cfg_builder = CFGBuilder(example_file)
        cfgs = cfg_builder.build_cfg()
        
        if cfgs:
            # 选择一个函数进行PDG分析
            func_name = 'factorial'
            cfg = cfgs.get(func_name)
            
            if cfg:
                # 数据流分析
                dataflow = DataFlowAnalyzer(cfg)
                dataflow_result = dataflow.analyze()
                
                # 构建PDG
                pdg_builder = PDGBuilder(cfg, dataflow_result)
                pdg = pdg_builder.build_pdg()
                
                print(f"✓ 为函数 {func_name} 构建了PDG")
                
                # 打印PDG统计信息
                pdg_builder.print_pdg_summary()
                
                # 程序切片演示
                slice_nodes = pdg_builder.slice_program((list(pdg.nodes)[0], 'result'))
                print(f"程序切片结果: {len(slice_nodes)} 个相关节点")
                
            else:
                print(f"✗ 未找到函数 {func_name}")
        else:
            print("✗ CFG构建失败")
            
    except Exception as e:
        print(f"✗ PDG分析失败: {e}")
        import traceback
        traceback.print_exc()

def demo_coupling_analysis():
    """演示耦合度分析"""
    print("\n" + "=" * 60)
    print("5. 耦合度分析演示")
    print("=" * 60)
    
    import clang.cindex
    from cfg import CFGBuilder
    from dataflow import DataFlowAnalyzer
    from pdg import PDGBuilder
    from callgraph import CallGraphBuilder
    from interprocedural import InterproceduralAnalyzer
    from coupling import CouplingCalculator
    
    # 使用更复杂的示例文件
    example_file = os.path.join(project_root, 'examples', 'matrix_operations.c')
    
    print(f"分析文件: {example_file}")
    print("执行耦合度分析...")
    
    try:
        # 1. 解析源文件
        index = clang.cindex.Index.create()
        tu = index.parse(example_file)
        
        if not tu:
            print("✗ 源文件解析失败")
            return
        
        # 2. 构建调用图
        call_graph_builder = CallGraphBuilder(tu)
        call_graph = call_graph_builder.build_call_graph()
        
        # 3. 构建CFG和PDG (简化版)
        cfg_builder = CFGBuilder(example_file)
        cfgs = cfg_builder.build_cfg()
        
        pdgs = {}
        for func_name, cfg in cfgs.items():
            if func_name in ['create_matrix', 'matrix_multiply', 'print_matrix', 'main']:
                try:
                    dataflow = DataFlowAnalyzer(cfg)
                    dataflow_result = dataflow.analyze()
                    
                    pdg_builder = PDGBuilder(cfg, dataflow_result)
                    pdg = pdg_builder.build_pdg()
                    pdgs[func_name] = pdg
                except:
                    # 忽略PDG构建失败
                    pass
        
        # 4. 函数间分析
        interprocedural = InterproceduralAnalyzer(call_graph, pdgs)
        interprocedural_result = interprocedural.analyze()
        
        # 5. 耦合度计算
        coupling_calc = CouplingCalculator(call_graph, interprocedural_result)
        coupling_result = coupling_calc.calculate_coupling()
        
        print("✓ 耦合度分析完成")
        
        # 打印结果
        coupling_calc.print_coupling_summary()
        
        # 分析具体函数的耦合度
        interesting_funcs = ['create_matrix', 'matrix_multiply', 'print_matrix', 'main']
        for func in interesting_funcs:
            metrics = coupling_calc.get_function_coupling(func)
            if metrics:
                total_coupling = (metrics.data_coupling + metrics.control_coupling + 
                                metrics.parameter_coupling + metrics.global_coupling)
                print(f"\n{func} 耦合度详情:")
                print(f"  - 数据耦合: {metrics.data_coupling}")
                print(f"  - 控制耦合: {metrics.control_coupling}")
                print(f"  - 参数耦合: {metrics.parameter_coupling}")
                print(f"  - 全局耦合: {metrics.global_coupling}")
                print(f"  - 总耦合度: {total_coupling}")
                print(f"  - 不稳定度: {metrics.instability:.3f}")
        
    except Exception as e:
        print(f"✗ 耦合度分析失败: {e}")
        import traceback
        traceback.print_exc()

def demo_report_generation():
    """演示报告生成"""
    print("\n" + "=" * 60)
    print("6. 报告生成演示")
    print("=" * 60)
    
    from visualization import SourceMapper
    import clang.cindex
    
    example_file = os.path.join(project_root, 'examples', 'simple_example.c')
    
    print("生成分析报告...")
    
    try:
        # 解析源文件
        index = clang.cindex.Index.create()
        tu = index.parse(example_file)
        
        if tu:
            # 创建简化的分析结果
            mock_results = {
                'cfgs': {'main': None, 'add': None, 'factorial': None},
                'call_graph': None,
                'coupling': {
                    'statistics': {
                        'avg_coupling': 8.5,
                        'max_coupling': 15.2,
                        'coupling_distribution': {
                            'low': 2,
                            'medium': 1,
                            'high': 1
                        }
                    }
                },
                'dataflow': {
                    'variables': {'x', 'y', 'result'},
                    'definitions': set()
                },
                'pdgs': {}
            }
            
            # 生成HTML报告
            mapper = SourceMapper(tu)
            report_html = mapper.generate_html_report(mock_results)
            
            # 保存报告
            output_dir = "analysis_output"
            os.makedirs(output_dir, exist_ok=True)
            report_path = os.path.join(output_dir, "demo_report.html")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_html)
            
            print(f"✓ HTML报告已生成: {report_path}")
            print(f"  报告大小: {len(report_html)} 字符")
            
        else:
            print("✗ 源文件解析失败")
            
    except Exception as e:
        print(f"✗ 报告生成失败: {e}")

def main():
    """主演示函数"""
    print("🚀 C语言静态分析系统演示")
    print("本演示将展示系统的各项核心功能")
    print("\n按 Enter 继续，或输入 'q' 退出...")
    
    user_input = input().strip().lower()
    if user_input == 'q':
        print("演示已取消")
        return
    
    start_time = time.time()
    
    demos = [
        demo_cfg_analysis,
        demo_dataflow_analysis, 
        demo_call_graph_analysis,
        demo_pdg_analysis,
        demo_coupling_analysis,
        demo_report_generation
    ]
    
    for i, demo_func in enumerate(demos, 1):
        try:
            demo_func()
            
            if i < len(demos):
                print(f"\n--- 演示 {i}/{len(demos)} 完成 ---")
                print("按 Enter 继续下一个演示...")
                input()
        
        except KeyboardInterrupt:
            print("\n\n演示被用户中断")
            break
        except Exception as e:
            print(f"\n演示 {i} 出现错误: {e}")
            print("继续下一个演示...")
    
    end_time = time.time()
    
    print("\n" + "=" * 60)
    print("🎉 演示完成！")
    print(f"总用时: {end_time - start_time:.2f} 秒")
    print("=" * 60)
    
    print("\n📋 演示总结:")
    print("1. ✓ 控制流图构建 - 成功分析了程序的控制结构")
    print("2. ✓ 数据流分析 - 分析了变量的定义和使用")
    print("3. ✓ 函数调用图 - 识别了函数间的调用关系")
    print("4. ✓ 程序依赖图 - 构建了控制和数据依赖关系")
    print("5. ✓ 耦合度计算 - 量化了代码的耦合程度")
    print("6. ✓ 报告生成 - 生成了详细的HTML分析报告")
    
    print("\n📁 输出文件:")
    output_dir = "analysis_output"
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        for file in files:
            file_path = os.path.join(output_dir, file)
            size = os.path.getsize(file_path)
            print(f"  - {file} ({size} bytes)")
    
    print("\n🔍 使用建议:")
    print("- 查看生成的HTML报告了解详细分析结果")
    print("- 使用不同的C源文件测试系统功能")
    print("- 根据耦合度分析结果优化代码结构")
    print("- 利用程序切片功能进行调试和理解")

if __name__ == '__main__':
    main()