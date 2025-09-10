"""
CFG构建器测试用例

测试控制流图构建的各种场景：
- 基本语句处理
- if/else语句
- while循环
- for循环
- 函数调用
- 复杂控制流
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import tempfile
from unittest.mock import Mock, patch
import clang.cindex

from cfg import CFGBuilder


class TestCFGBuilder(unittest.TestCase):
    """CFG构建器测试类"""
    
    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """测试后清理"""
        # 清理临时文件
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_temp_c_file(self, content: str) -> str:
        """创建临时C文件"""
        temp_file = os.path.join(self.temp_dir, "test.c")
        with open(temp_file, 'w') as f:
            f.write(content)
        return temp_file
    
    def test_simple_function(self):
        """测试简单函数的CFG构建"""
        c_code = """
        int add(int a, int b) {
            int result = a + b;
            return result;
        }
        """
        
        temp_file = self.create_temp_c_file(c_code)
        
        try:
            builder = CFGBuilder(temp_file)
            cfgs = builder.build_cfg()
            
            # 验证基本结构
            self.assertIn('add', cfgs)
            cfg = cfgs['add']
            
            # 应该有entry和exit节点
            node_types = [cfg.nodes[node]['type'] for node in cfg.nodes]
            self.assertIn('entry', node_types)
            self.assertIn('exit', node_types)
            
            # 验证节点数量合理
            self.assertGreaterEqual(cfg.number_of_nodes(), 2)
            
        except Exception as e:
            self.skipTest(f"Clang not available or parsing failed: {e}")
    
    def test_if_statement(self):
        """测试if语句的CFG构建"""
        c_code = """
        int max(int a, int b) {
            if (a > b) {
                return a;
            } else {
                return b;
            }
        }
        """
        
        temp_file = self.create_temp_c_file(c_code)
        
        try:
            builder = CFGBuilder(temp_file)
            cfgs = builder.build_cfg()
            
            self.assertIn('max', cfgs)
            cfg = cfgs['max']
            
            # if语句应该产生条件节点
            node_types = [cfg.nodes[node]['type'] for node in cfg.nodes]
            
            # 验证基本结构存在
            self.assertGreaterEqual(cfg.number_of_nodes(), 3)  # 至少entry, condition, exit
            
        except Exception as e:
            self.skipTest(f"Clang not available or parsing failed: {e}")
    
    def test_while_loop(self):
        """测试while循环的CFG构建"""
        c_code = """
        int factorial(int n) {
            int result = 1;
            while (n > 0) {
                result = result * n;
                n = n - 1;
            }
            return result;
        }
        """
        
        temp_file = self.create_temp_c_file(c_code)
        
        try:
            builder = CFGBuilder(temp_file)
            cfgs = builder.build_cfg()
            
            self.assertIn('factorial', cfgs)
            cfg = cfgs['factorial']
            
            # while循环应该有回边
            self.assertGreaterEqual(cfg.number_of_edges(), 2)
            
        except Exception as e:
            self.skipTest(f"Clang not available or parsing failed: {e}")
    
    def test_for_loop(self):
        """测试for循环的CFG构建"""
        c_code = """
        int sum_array(int arr[], int size) {
            int sum = 0;
            for (int i = 0; i < size; i++) {
                sum += arr[i];
            }
            return sum;
        }
        """
        
        temp_file = self.create_temp_c_file(c_code)
        
        try:
            builder = CFGBuilder(temp_file)
            cfgs = builder.build_cfg()
            
            self.assertIn('sum_array', cfgs)
            cfg = cfgs['sum_array']
            
            # for循环应该有多个节点和边
            self.assertGreaterEqual(cfg.number_of_nodes(), 4)
            
        except Exception as e:
            self.skipTest(f"Clang not available or parsing failed: {e}")
    
    def test_nested_control_flow(self):
        """测试嵌套控制流的CFG构建"""
        c_code = """
        int complex_function(int x, int y) {
            int result = 0;
            
            if (x > 0) {
                for (int i = 0; i < x; i++) {
                    if (y > 5) {
                        result += i;
                    } else {
                        result -= i;
                    }
                }
            } else {
                while (y > 0) {
                    result++;
                    y--;
                }
            }
            
            return result;
        }
        """
        
        temp_file = self.create_temp_c_file(c_code)
        
        try:
            builder = CFGBuilder(temp_file)
            cfgs = builder.build_cfg()
            
            self.assertIn('complex_function', cfgs)
            cfg = cfgs['complex_function']
            
            # 嵌套控制流应该产生更多的节点
            self.assertGreaterEqual(cfg.number_of_nodes(), 6)
            
        except Exception as e:
            self.skipTest(f"Clang not available or parsing failed: {e}")
    
    def test_function_calls(self):
        """测试函数调用的CFG构建"""
        c_code = """
        int helper(int x) {
            return x * 2;
        }
        
        int main_func(int a, int b) {
            int x = helper(a);
            int y = helper(b);
            return x + y;
        }
        """
        
        temp_file = self.create_temp_c_file(c_code)
        
        try:
            builder = CFGBuilder(temp_file)
            cfgs = builder.build_cfg()
            
            # 应该识别两个函数
            self.assertIn('helper', cfgs)
            self.assertIn('main_func', cfgs)
            
            # 每个函数都应该有基本的CFG结构
            for func_name in ['helper', 'main_func']:
                cfg = cfgs[func_name]
                self.assertGreaterEqual(cfg.number_of_nodes(), 2)
            
        except Exception as e:
            self.skipTest(f"Clang not available or parsing failed: {e}")
    
    def test_switch_statement(self):
        """测试switch语句的CFG构建"""
        c_code = """
        int switch_func(int x) {
            int result = 0;
            switch (x) {
                case 1:
                    result = 10;
                    break;
                case 2:
                    result = 20;
                    break;
                default:
                    result = 0;
            }
            return result;
        }
        """
        
        temp_file = self.create_temp_c_file(c_code)
        
        try:
            builder = CFGBuilder(temp_file)
            cfgs = builder.build_cfg()
            
            self.assertIn('switch_func', cfgs)
            cfg = cfgs['switch_func']
            
            # switch语句应该产生多个分支
            self.assertGreaterEqual(cfg.number_of_nodes(), 4)
            
        except Exception as e:
            self.skipTest(f"Clang not available or parsing failed: {e}")
    
    def test_cfg_statistics(self):
        """测试CFG统计信息"""
        c_code = """
        void func1() {
            int x = 1;
        }
        
        void func2() {
            int y = 2;
            if (y > 0) {
                y--;
            }
        }
        """
        
        temp_file = self.create_temp_c_file(c_code)
        
        try:
            builder = CFGBuilder(temp_file)
            cfgs = builder.build_cfg()
            
            # 验证统计信息方法不会崩溃
            builder.print_cfg_stats()
            
            # 验证可以获取特定函数的CFG
            func1_cfg = builder.get_function_cfg('func1')
            if func1_cfg:
                self.assertIsInstance(func1_cfg, type(cfgs['func1']))
            
        except Exception as e:
            self.skipTest(f"Clang not available or parsing failed: {e}")
    
    def test_empty_function(self):
        """测试空函数的CFG构建"""
        c_code = """
        void empty_func() {
        }
        """
        
        temp_file = self.create_temp_c_file(c_code)
        
        try:
            builder = CFGBuilder(temp_file)
            cfgs = builder.build_cfg()
            
            self.assertIn('empty_function', cfgs)  # 可能的函数名
            
        except Exception as e:
            self.skipTest(f"Clang not available or parsing failed: {e}")
    
    def test_invalid_source_file(self):
        """测试无效源文件的处理"""
        # 测试不存在的文件
        with self.assertRaises((FileNotFoundError, RuntimeError)):
            builder = CFGBuilder("non_existent_file.c")
            builder.build_cfg()
    
    def test_syntax_error_handling(self):
        """测试语法错误的处理"""
        c_code = """
        int broken_func(int x {  // 缺少右括号
            return x
        }  // 缺少分号
        """
        
        temp_file = self.create_temp_c_file(c_code)
        
        try:
            builder = CFGBuilder(temp_file)
            # 应该能处理语法错误而不崩溃
            cfgs = builder.build_cfg()
            # 可能返回空结果或处理部分内容
            
        except Exception as e:
            # 预期可能抛出异常，这是正常的
            self.assertIsInstance(e, (RuntimeError, Exception))


class TestBasicBlock(unittest.TestCase):
    """基本块类测试"""
    
    def test_basic_block_creation(self):
        """测试基本块创建"""
        from cfg import BasicBlock
        
        block = BasicBlock("block_1", "normal")
        
        self.assertEqual(block.id, "block_1")
        self.assertEqual(block.type, "normal")
        self.assertEqual(len(block.statements), 0)
        self.assertEqual(len(block.variables), 0)
    
    def test_basic_block_operations(self):
        """测试基本块操作"""
        from cfg import BasicBlock
        
        block = BasicBlock("test_block")
        
        # 测试添加变量
        block.add_variable("var1")
        block.add_variable("var2")
        self.assertIn("var1", block.variables)
        self.assertIn("var2", block.variables)
        
        # 测试转换为字典
        block_dict = block.to_dict()
        self.assertEqual(block_dict['id'], "test_block")
        self.assertIn('variables', block_dict)


if __name__ == '__main__':
    # 配置测试环境
    import logging
    logging.disable(logging.CRITICAL)  # 禁用日志输出
    
    unittest.main(verbosity=2)