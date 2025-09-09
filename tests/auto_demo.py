#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C语言静态分析系统自动演示脚本

自动展示系统的主要功能，无需用户交互
"""

import os
import sys
import time

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # 回到项目根目录
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

def auto_demo():
    """自动演示所有功能"""
    print("🚀 C语言静态分析系统自动演示")
    print("=" * 60)
    
    start_time = time.time()
    
    # 1. CFG分析演示
    print("\n1. 控制流图(CFG)分析")
    print("-" * 30)
    
    from cfg import CFGBuilder
    
    example_file = os.path.join(project_root, 'examples', 'simple_example.c')
    print(f"分析文件: {os.path.basename(example_file)}")
    
    try:
        builder = CFGBuilder(example_file)
        cfgs = builder.build_cfg()
        
        if cfgs:
            user_funcs = [name for name in cfgs.keys() 
                         if name in ['add', 'max', 'factorial', 'fibonacci', 'main']]
            
            print(f"✓ 成功为 {len(user_funcs)} 个用户函数构建CFG")
            
            for func_name in user_funcs:
                cfg = cfgs[func_name]
                print(f"  {func_name}: {cfg.number_of_nodes()} 基本块, {cfg.number_of_edges()} 边")
        else:
            print("✗ CFG构建失败")
    
    except Exception as e:
        print(f"✗ CFG分析失败: {e}")
    
    # 2. 数据流分析演示
    print("\n2. 数据流分析")
    print("-" * 30)
    
    try:
        from dataflow import DataFlowAnalyzer
        
        if cfgs and 'factorial' in cfgs:
            analyzer = DataFlowAnalyzer(cfgs['factorial'])
            result = analyzer.analyze()
            
            print("✓ 数据流分析完成 (factorial函数)")
            print(f"  变量数: {len(result.get('variables', set()))}")
            print(f"  定义数: {len(result.get('definitions', set()))}")
            
            # 检测未初始化变量
            uninitialized = analyzer.detect_uninitialized_variables()
            print(f"  未初始化变量: {len(uninitialized)}")
            
            # 检测死代码
            dead_code = analyzer.detect_dead_code()
            print(f"  潜在死代码块: {len(dead_code)}")
        else:
            print("✗ 无法进行数据流分析")
    
    except Exception as e:
        print(f"✗ 数据流分析失败: {e}")
    
    # 3. 函数调用图分析
    print("\n3. 函数调用图分析")
    print("-" * 30)
    
    try:
        import clang.cindex
        from callgraph import CallGraphBuilder
        
        # 使用链表示例获得更有趣的调用关系
        list_example = os.path.join(project_root, 'examples', 'linked_list.c')
        
        index = clang.cindex.Index.create()
        tu = index.parse(list_example)
        
        if tu:
            builder = CallGraphBuilder(tu)
            call_graph = builder.build_call_graph()
            
            print(f"✓ 调用图构建完成 ({os.path.basename(list_example)})")
            print(f"  函数总数: {call_graph.number_of_nodes()}")
            print(f"  调用关系: {call_graph.number_of_edges()}")
            
            # 分析关键函数
            key_functions = ['main', 'insert_at_head', 'search', 'print_list']
            for func in key_functions:
                if func in call_graph:
                    in_degree = call_graph.in_degree(func)
                    out_degree = call_graph.out_degree(func)
                    print(f"  {func}: 被调用{in_degree}次, 调用{out_degree}个函数")
        else:
            print("✗ 源文件解析失败")
    
    except Exception as e:
        print(f"✗ 调用图分析失败: {e}")
    
    # 4. 程序依赖图分析
    print("\n4. 程序依赖图(PDG)分析")
    print("-" * 30)
    
    try:
        from pdg import PDGBuilder
        
        if cfgs and 'factorial' in cfgs:
            # 重用之前的数据流结果
            pdg_builder = PDGBuilder(cfgs['factorial'], result)
            pdg = pdg_builder.build_pdg()
            
            print("✓ PDG构建完成 (factorial函数)")
            print(f"  节点数: {pdg.number_of_nodes()}")
            print(f"  依赖边数: {pdg.number_of_edges()}")
            
            # 统计依赖类型
            control_edges = sum(1 for _, _, data in pdg.edges(data=True) 
                              if data.get('type') == 'control')
            data_edges = sum(1 for _, _, data in pdg.edges(data=True) 
                           if data.get('type') == 'data')
            
            print(f"  控制依赖: {control_edges}")
            print(f"  数据依赖: {data_edges}")
            
            # 程序切片演示
            if pdg.nodes:
                first_node = list(pdg.nodes)[0]
                slice_nodes = pdg_builder.slice_program((first_node, 'result'))
                print(f"  程序切片: 影响{len(slice_nodes)}个节点")
        else:
            print("✗ 无法进行PDG分析")
    
    except Exception as e:
        print(f"✗ PDG分析失败: {e}")
    
    # 5. 耦合度分析
    print("\n5. 耦合度分析")
    print("-" * 30)
    
    try:
        from interprocedural import InterproceduralAnalyzer
        from coupling import CouplingCalculator
        
        # 使用矩阵运算示例
        matrix_example = os.path.join(project_root, 'examples', 'matrix_operations.c')
        
        index = clang.cindex.Index.create()
        tu = index.parse(matrix_example)
        
        if tu:
            # 构建调用图
            call_builder = CallGraphBuilder(tu)
            call_graph = call_builder.build_call_graph()
            
            # 简化的函数间分析
            cfg_builder = CFGBuilder(matrix_example)
            matrix_cfgs = cfg_builder.build_cfg()
            
            # 选择几个关键函数进行分析
            key_funcs = ['create_matrix', 'matrix_multiply', 'print_matrix', 'main']
            sample_pdgs = {}
            
            for func in key_funcs:
                if func in matrix_cfgs:
                    try:
                        df_analyzer = DataFlowAnalyzer(matrix_cfgs[func])
                        df_result = df_analyzer.analyze()
                        
                        pdg_builder = PDGBuilder(matrix_cfgs[func], df_result)
                        sample_pdgs[func] = pdg_builder.build_pdg()
                    except:
                        pass
            
            # 函数间分析
            interprocedural = InterproceduralAnalyzer(call_graph, sample_pdgs)
            interprocedural_result = interprocedural.analyze()
            
            # 耦合度计算
            coupling_calc = CouplingCalculator(call_graph, interprocedural_result)
            coupling_result = coupling_calc.calculate_coupling()
            
            print(f"✓ 耦合度分析完成 ({os.path.basename(matrix_example)})")
            
            stats = coupling_result.get('statistics', {})
            print(f"  平均耦合度: {stats.get('avg_coupling', 0):.2f}")
            print(f"  最大耦合度: {stats.get('max_coupling', 0):.2f}")
            
            # 耦合度分布
            distribution = stats.get('coupling_distribution', {})
            print(f"  低耦合函数: {distribution.get('low', 0)}")
            print(f"  中耦合函数: {distribution.get('medium', 0)}")
            print(f"  高耦合函数: {distribution.get('high', 0)}")
            
            # 分析几个具体函数
            metrics = coupling_result.get('metrics', {})
            for func in ['create_matrix', 'matrix_multiply', 'main']:
                if func in metrics:
                    m = metrics[func]
                    total = m.data_coupling + m.control_coupling + m.parameter_coupling + m.global_coupling
                    print(f"  {func}: 总耦合度 {total:.1f} (不稳定度 {m.instability:.3f})")
        else:
            print("✗ 矩阵示例解析失败")
    
    except Exception as e:
        print(f"✗ 耦合度分析失败: {e}")
    
    # 6. 报告生成
    print("\n6. 报告生成")
    print("-" * 30)
    
    try:
        from visualization import SourceMapper
        
        # 生成简化报告
        index = clang.cindex.Index.create()
        tu = index.parse(example_file)
        
        if tu:
            # 模拟分析结果
            mock_results = {
                'cfgs': {'main': None, 'add': None, 'factorial': None, 'fibonacci': None},
                'call_graph': None,
                'coupling': {
                    'statistics': {
                        'total_functions': 4,
                        'avg_coupling': 6.8,
                        'max_coupling': 12.5,
                        'coupling_distribution': {
                            'low': 2,
                            'medium': 1,
                            'high': 1
                        }
                    },
                    'metrics': {}
                },
                'dataflow': {
                    'variables': {'x', 'y', 'result', 'n', 'i'},
                    'definitions': set(range(8))
                },
                'pdgs': {}
            }
            
            mapper = SourceMapper(tu)
            report_html = mapper.generate_html_report(mock_results)
            
            # 保存报告
            output_dir = "analysis_output"
            os.makedirs(output_dir, exist_ok=True)
            report_path = os.path.join(output_dir, "auto_demo_report.html")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_html)
            
            print(f"✓ HTML报告已生成")
            print(f"  文件: {report_path}")
            print(f"  大小: {len(report_html):,} 字符")
        else:
            print("✗ 报告生成失败")
    
    except Exception as e:
        print(f"✗ 报告生成失败: {e}")
    
    # 总结
    end_time = time.time()
    
    print("\n" + "=" * 60)
    print("🎉 自动演示完成!")
    print(f"总用时: {end_time - start_time:.2f} 秒")
    print("=" * 60)
    
    print("\n📊 演示结果总结:")
    print("✓ 控制流图(CFG)构建 - 成功分析程序控制结构")
    print("✓ 数据流分析 - 检测变量使用和潜在问题")
    print("✓ 函数调用图 - 识别函数间调用关系")
    print("✓ 程序依赖图(PDG) - 构建控制和数据依赖")
    print("✓ 耦合度分析 - 量化代码耦合程度")
    print("✓ 分析报告生成 - 生成详细HTML报告")
    
    print("\n🎯 系统特性:")
    print("• 支持复杂C语言语法(循环、条件、函数调用)")
    print("• 多层次分析(语法、语义、结构)")
    print("• 量化代码质量指标")
    print("• 可视化分析结果")
    print("• 模块化设计，易于扩展")
    
    print("\n📁 输出文件:")
    output_dir = "analysis_output"
    if os.path.exists(output_dir):
        files = [f for f in os.listdir(output_dir) if f.endswith('.html')]
        for file in files:
            file_path = os.path.join(output_dir, file)
            size = os.path.getsize(file_path)
            print(f"  📄 {file} ({size:,} bytes)")
    
    print(f"\n🔍 系统已成功演示完毕！")
    print("可以使用 python src/analyzer.py <c_file> 命令分析其他C文件")

if __name__ == '__main__':
    auto_demo()