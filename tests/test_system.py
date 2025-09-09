#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单的测试脚本，用于验证C语言静态分析系统的基本功能
"""

import os
import sys
import tempfile

def create_test_file():
    """创建一个简单的测试C文件"""
    c_code = """
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main() {
    int result = add(5, 3);
    printf("Result: %d\\n", result);
    return 0;
}
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(c_code)
        return f.name

def test_clang_availability():
    """测试Clang是否可用"""
    try:
        import clang.cindex
        print("✓ Clang Python bindings available")
        
        # 尝试创建索引
        index = clang.cindex.Index.create()
        print("✓ Clang index created successfully")
        
        return True
    except ImportError as e:
        print(f"✗ Clang not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Clang error: {e}")
        return False

def test_basic_parsing():
    """测试基本的源码解析"""
    try:
        import clang.cindex
        
        test_file = create_test_file()
        print(f"Created test file: {test_file}")
        
        # 解析文件
        index = clang.cindex.Index.create()
        tu = index.parse(test_file)
        
        if tu is None:
            print("✗ Failed to parse test file")
            return False
        
        print("✓ Successfully parsed test file")
        
        # 统计函数
        functions = []
        for node in tu.cursor.walk_preorder():
            if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
                functions.append(node.spelling)
        
        print(f"✓ Found functions: {functions}")
        
        # 清理
        os.unlink(test_file)
        
        return len(functions) > 0
        
    except Exception as e:
        print(f"✗ Parsing test failed: {e}")
        return False

def test_networkx():
    """测试NetworkX图库"""
    try:
        import networkx as nx
        
        # 创建简单图
        G = nx.DiGraph()
        G.add_node("main")
        G.add_node("add")
        G.add_edge("main", "add")
        
        print("✓ NetworkX working correctly")
        print(f"  Graph nodes: {G.number_of_nodes()}")
        print(f"  Graph edges: {G.number_of_edges()}")
        
        return True
        
    except ImportError as e:
        print(f"✗ NetworkX not available: {e}")
        return False
    except Exception as e:
        print(f"✗ NetworkX error: {e}")
        return False

def test_basic_cfg():
    """测试基本的CFG构建"""
    try:
        # 添加src目录到Python路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)  # 回到项目根目录
        src_dir = os.path.join(project_root, 'src')
        sys.path.insert(0, src_dir)
        
        from cfg import CFGBuilder, BasicBlock
        
        print("✓ CFG module imported successfully")
        
        # 测试基本块创建
        block = BasicBlock("test_block", "normal")
        block.add_variable("x")
        block.add_variable("y")
        
        block_dict = block.to_dict()
        assert block_dict['id'] == "test_block"
        assert len(block_dict['variables']) == 2
        
        print("✓ BasicBlock creation and operations work")
        
        return True
        
    except ImportError as e:
        print(f"✗ CFG module import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ CFG test failed: {e}")
        return False

def run_integration_test():
    """运行集成测试"""
    try:
        # 添加src目录到Python路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)  # 回到项目根目录
        src_dir = os.path.join(project_root, 'src')
        sys.path.insert(0, src_dir)
        
        # 使用示例文件进行测试
        example_file = os.path.join(project_root, 'examples', 'simple_example.c')
        
        if not os.path.exists(example_file):
            print(f"✗ Example file not found: {example_file}")
            return False
        
        from cfg import CFGBuilder
        
        print(f"Testing CFG building with: {example_file}")
        
        builder = CFGBuilder(example_file)
        cfgs = builder.build_cfg()
        
        if cfgs:
            print(f"✓ Successfully built CFGs for {len(cfgs)} functions")
            for func_name, cfg in cfgs.items():
                print(f"  {func_name}: {cfg.number_of_nodes()} blocks, {cfg.number_of_edges()} edges")
            return True
        else:
            print("✗ No CFGs generated")
            return False
            
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("C Static Analysis System - Basic Tests")
    print("=" * 50)
    
    tests = [
        ("Clang Availability", test_clang_availability),
        ("Basic Parsing", test_basic_parsing),
        ("NetworkX", test_networkx),
        ("Basic CFG", test_basic_cfg),
        ("Integration Test", run_integration_test)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print(f"\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())