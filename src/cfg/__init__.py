"""
控制流图(CFG)构建模块

本模块实现了C语言源码的控制流图构建功能，支持：
- 基本块分割
- if/else语句处理
- while/for循环处理  
- switch语句处理
- 函数调用处理
- 复合语句处理
"""

import clang.cindex
from clang.cindex import CursorKind, TranslationUnit, TokenKind
import networkx as nx
from typing import Dict, List, Set, Optional, Tuple, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BasicBlock:
    """基本块类"""
    
    def __init__(self, block_id: str, block_type: str = "normal"):
        self.id = block_id
        self.type = block_type  # entry, exit, normal, condition, merge
        self.statements: List[Any] = []
        self.location: Optional[Any] = None
        self.variables: Set[str] = set()
        self.predecessors: Set[str] = set()
        self.successors: Set[str] = set()
    
    def add_statement(self, stmt: Any):
        """添加语句到基本块"""
        self.statements.append(stmt)
        if not self.location and hasattr(stmt, 'location'):
            self.location = stmt.location
    
    def add_variable(self, var_name: str):
        """添加变量引用"""
        self.variables.add(var_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            'id': self.id,
            'type': self.type,
            'statements': len(self.statements),
            'location': self.location,
            'variables': list(self.variables)
        }

class CFGBuilder:
    """控制流图构建器"""
    
    def __init__(self, source_file: str):
        """
        初始化CFG构建器
        
        Args:
            source_file: C源文件路径
        """
        self.source_file = source_file
        self.index = clang.cindex.Index.create()
        self.tu = None
        self.cfg = nx.DiGraph()
        self.current_block = None
        self.block_counter = 0
        self.break_targets = []  # break语句的目标块
        self.continue_targets = []  # continue语句的目标块
        self.function_cfgs = {}  # 每个函数的CFG
        
        # 设置Clang解析选项
        self.parse_options = [
            '-std=c11',
            '-I.',
            '-Wall',
            '-Wextra'
        ]
    
    def build_cfg(self) -> Dict[str, nx.DiGraph]:
        """
        构建控制流图
        
        Returns:
            Dict[str, nx.DiGraph]: 函数名到CFG的映射
        """
        try:
            # 解析源文件
            self.tu = self.index.parse(
                self.source_file, 
                args=self.parse_options
            )
            
            if not self.tu:
                raise RuntimeError(f"Failed to parse {self.source_file}")
            
            # 检查解析错误
            diagnostics = list(self.tu.diagnostics)
            if diagnostics:
                for diag in diagnostics:
                    if diag.severity >= clang.cindex.Diagnostic.Error:
                        logger.error(f"Parse error: {diag.spelling}")
                    else:
                        logger.warning(f"Parse warning: {diag.spelling}")
            
            # 遍历所有函数，只处理用户定义的函数
            for node in self.tu.cursor.walk_preorder():
                if (node.kind == CursorKind.FUNCTION_DECL and 
                    node.is_definition() and 
                    self._is_user_function(node)):
                    logger.info(f"Processing function: {node.spelling}")
                    self._process_function(node)
            
            return self.function_cfgs
            
        except Exception as e:
            logger.error(f"Error building CFG: {str(e)}")
            raise
    
    def _is_user_function(self, func_node: Any) -> bool:
        """
        判断是否为用户定义的函数（排除系统函数）
        
        Args:
            func_node: 函数AST节点
            
        Returns:
            bool: 是否为用户函数
        """
        # 获取函数位置
        if not func_node.location or not func_node.location.file:
            return False
            
        # 只处理当前源文件中的函数
        func_file = func_node.location.file.name
        if not func_file.endswith(self.source_file.split('/')[-1].split('\\')[-1]):
            return False
            
        # 排除常见的系统函数名前缀
        func_name = func_node.spelling
        system_prefixes = [
            '__',           # 系统内部函数
            '_CRT',         # Windows CRT
            '_acrt',        # Windows ACRT
            '_stdio',       # stdio内部
            '_local',       # 本地化函数
            '_invoke',      # 调用相关
            '_invalid',     # 错误处理
            '_report',      # 报告函数
            '_security'     # 安全函数
        ]
        
        for prefix in system_prefixes:
            if func_name.startswith(prefix):
                return False
                
        # 排除常见的标准库函数
        system_functions = {
            'malloc', 'free', 'calloc', 'realloc',  # 内存管理
            'printf', 'scanf', 'sprintf', 'sscanf',  # 输入输出
            'fopen', 'fclose', 'fread', 'fwrite',    # 文件操作
            'strlen', 'strcpy', 'strcmp', 'strcat',  # 字符串
            'memcpy', 'memset', 'memcmp',            # 内存操作
            'exit', 'abort', 'atexit',               # 程序控制
            'rand', 'srand', 'time',                 # 其他常用函数
        }
        
        if func_name in system_functions:
            return False
            
        return True
    
    def _process_function(self, func_node: Any):
        """
        处理单个函数
        
        Args:
            func_node: 函数AST节点
        """
        func_name = func_node.spelling
        self.cfg = nx.DiGraph()
        self.block_counter = 0
        self.break_targets = []
        self.continue_targets = []
        
        # 创建入口块
        entry_block = self._create_block("entry")
        self.cfg.add_node(entry_block.id, **entry_block.to_dict())
        self.current_block = entry_block.id
        
        # 处理函数参数
        for param in func_node.get_children():
            if param.kind == CursorKind.PARM_DECL:
                entry_block.add_variable(param.spelling)
        
        # 处理函数体
        body = None
        for child in func_node.get_children():
            if child.kind == CursorKind.COMPOUND_STMT:
                body = child
                break
        
        if body:
            exit_block_id = self._process_compound_stmt(body)
            
            # 创建出口块
            exit_block = self._create_block("exit")
            self.cfg.add_node(exit_block.id, **exit_block.to_dict())
            
            # 连接到出口块
            if exit_block_id:
                self._add_edge(exit_block_id, exit_block.id)
            elif self.current_block:
                self._add_edge(self.current_block, exit_block.id)
        else:
            # 空函数体
            exit_block = self._create_block("exit")
            self.cfg.add_node(exit_block.id, **exit_block.to_dict())
            self._add_edge(entry_block.id, exit_block.id)
        
        self.function_cfgs[func_name] = self.cfg.copy()
    
    def _process_compound_stmt(self, compound_stmt: Any) -> Optional[str]:
        """
        处理复合语句
        
        Args:
            compound_stmt: 复合语句AST节点
            
        Returns:
            Optional[str]: 最后一个处理的块ID
        """
        last_block = self.current_block
        
        for stmt in compound_stmt.get_children():
            last_block = self._process_statement(stmt)
            if last_block is None:
                break
        
        return last_block
    
    def _process_statement(self, stmt: Any) -> Optional[str]:
        """
        处理单个语句
        
        Args:
            stmt: 语句AST节点
            
        Returns:
            Optional[str]: 处理后的当前块ID
        """
        if stmt.kind == CursorKind.IF_STMT:
            return self._process_if_stmt(stmt)
        elif stmt.kind == CursorKind.WHILE_STMT:
            return self._process_while_stmt(stmt)
        elif stmt.kind == CursorKind.FOR_STMT:
            return self._process_for_stmt(stmt)
        elif stmt.kind == CursorKind.SWITCH_STMT:
            return self._process_switch_stmt(stmt)
        elif stmt.kind == CursorKind.RETURN_STMT:
            return self._process_return_stmt(stmt)
        elif stmt.kind == CursorKind.BREAK_STMT:
            return self._process_break_stmt(stmt)
        elif stmt.kind == CursorKind.CONTINUE_STMT:
            return self._process_continue_stmt(stmt)
        elif stmt.kind == CursorKind.COMPOUND_STMT:
            return self._process_compound_stmt(stmt)
        else:
            # 普通语句，添加到当前块
            return self._process_normal_stmt(stmt)
    
    def _process_if_stmt(self, if_stmt: Any) -> Optional[str]:
        """处理if语句"""
        # 创建条件块
        cond_block = self._create_block("condition")
        cond_block.add_statement(if_stmt)
        self.cfg.add_node(cond_block.id, **cond_block.to_dict())
        
        # 连接当前块到条件块
        if self.current_block:
            self._add_edge(self.current_block, cond_block.id)
        
        # 获取then和else语句
        children = list(if_stmt.get_children())
        condition = children[0] if len(children) > 0 else None
        then_stmt = children[1] if len(children) > 1 else None
        else_stmt = children[2] if len(children) > 2 else None
        
        # 处理条件表达式中的变量
        if condition:
            self._extract_variables(condition, cond_block)
        
        # 创建汇合块
        merge_block = self._create_block("merge")
        self.cfg.add_node(merge_block.id, **merge_block.to_dict())
        
        # 处理then分支
        if then_stmt:
            self.current_block = cond_block.id
            then_last = self._process_statement(then_stmt)
            if then_last:
                self._add_edge(then_last, merge_block.id)
        else:
            self._add_edge(cond_block.id, merge_block.id)
        
        # 处理else分支
        if else_stmt:
            self.current_block = cond_block.id
            else_last = self._process_statement(else_stmt)
            if else_last:
                self._add_edge(else_last, merge_block.id)
        else:
            self._add_edge(cond_block.id, merge_block.id)
        
        return merge_block.id
    
    def _process_while_stmt(self, while_stmt: Any) -> Optional[str]:
        """处理while语句"""
        # 创建循环条件块
        loop_cond = self._create_block("loop_condition")
        loop_cond.add_statement(while_stmt)
        self.cfg.add_node(loop_cond.id, **loop_cond.to_dict())
        
        # 连接当前块到条件块
        if self.current_block:
            self._add_edge(self.current_block, loop_cond.id)
        
        # 创建循环体块和后续块
        loop_exit = self._create_block("loop_exit")
        self.cfg.add_node(loop_exit.id, **loop_exit.to_dict())
        
        # 设置break和continue目标
        old_break = self.break_targets.copy()
        old_continue = self.continue_targets.copy()
        self.break_targets.append(loop_exit.id)
        self.continue_targets.append(loop_cond.id)
        
        # 获取循环体
        children = list(while_stmt.get_children())
        condition = children[0] if len(children) > 0 else None
        body = children[1] if len(children) > 1 else None
        
        # 处理条件表达式
        if condition:
            self._extract_variables(condition, loop_cond)
        
        # 处理循环体
        if body:
            self.current_block = loop_cond.id
            body_last = self._process_statement(body)
            if body_last:
                # 循环体结束后回到条件块
                self._add_edge(body_last, loop_cond.id)
        
        # 条件为假时退出循环
        self._add_edge(loop_cond.id, loop_exit.id)
        
        # 恢复break和continue目标
        self.break_targets = old_break
        self.continue_targets = old_continue
        
        return loop_exit.id
    
    def _process_for_stmt(self, for_stmt: Any) -> Optional[str]:
        """处理for语句"""
        # for语句结构: init; condition; increment; body
        children = list(for_stmt.get_children())
        
        # 创建初始化块
        init_block = self._create_block("for_init")
        if len(children) > 0:  # init
            init_block.add_statement(children[0])
            self._extract_variables(children[0], init_block)
        self.cfg.add_node(init_block.id, **init_block.to_dict())
        
        # 连接当前块到初始化块
        if self.current_block:
            self._add_edge(self.current_block, init_block.id)
        
        # 创建条件块
        cond_block = self._create_block("for_condition")
        if len(children) > 1:  # condition
            cond_block.add_statement(children[1])
            self._extract_variables(children[1], cond_block)
        self.cfg.add_node(cond_block.id, **cond_block.to_dict())
        self._add_edge(init_block.id, cond_block.id)
        
        # 创建增量块
        incr_block = self._create_block("for_increment")
        if len(children) > 2:  # increment
            incr_block.add_statement(children[2])
            self._extract_variables(children[2], incr_block)
        self.cfg.add_node(incr_block.id, **incr_block.to_dict())
        
        # 创建退出块
        exit_block = self._create_block("for_exit")
        self.cfg.add_node(exit_block.id, **exit_block.to_dict())
        
        # 设置break和continue目标
        old_break = self.break_targets.copy()
        old_continue = self.continue_targets.copy()
        self.break_targets.append(exit_block.id)
        self.continue_targets.append(incr_block.id)
        
        # 处理循环体
        if len(children) > 3:  # body
            self.current_block = cond_block.id
            body_last = self._process_statement(children[3])
            if body_last:
                self._add_edge(body_last, incr_block.id)
        
        # 连接增量块回到条件块
        self._add_edge(incr_block.id, cond_block.id)
        
        # 条件为假时退出
        self._add_edge(cond_block.id, exit_block.id)
        
        # 恢复break和continue目标
        self.break_targets = old_break
        self.continue_targets = old_continue
        
        return exit_block.id
    
    def _process_switch_stmt(self, switch_stmt: Any) -> Optional[str]:
        """处理switch语句"""
        # 创建switch条件块
        switch_block = self._create_block("switch")
        switch_block.add_statement(switch_stmt)
        self.cfg.add_node(switch_block.id, **switch_block.to_dict())
        
        if self.current_block:
            self._add_edge(self.current_block, switch_block.id)
        
        # 创建退出块
        exit_block = self._create_block("switch_exit")
        self.cfg.add_node(exit_block.id, **exit_block.to_dict())
        
        # 设置break目标
        old_break = self.break_targets.copy()
        self.break_targets.append(exit_block.id)
        
        # 处理switch体中的case语句
        children = list(switch_stmt.get_children())
        if len(children) > 1:
            switch_body = children[1]
            case_blocks = []
            
            for stmt in switch_body.get_children():
                if stmt.kind == CursorKind.CASE_STMT or stmt.kind == CursorKind.DEFAULT_STMT:
                    case_block = self._create_block("case")
                    case_block.add_statement(stmt)
                    self.cfg.add_node(case_block.id, **case_block.to_dict())
                    case_blocks.append(case_block.id)
                    
                    # switch块连接到每个case
                    self._add_edge(switch_block.id, case_block.id)
                    
                    # 处理case体
                    self.current_block = case_block.id
                    self._process_statement(stmt)
            
            # 如果没有显式的break，case会fall through
            for i in range(len(case_blocks) - 1):
                self._add_edge(case_blocks[i], case_blocks[i + 1])
            
            # 最后一个case连接到退出块
            if case_blocks:
                self._add_edge(case_blocks[-1], exit_block.id)
        
        # 恢复break目标
        self.break_targets = old_break
        
        return exit_block.id
    
    def _process_return_stmt(self, return_stmt: Any) -> Optional[str]:
        """处理return语句"""
        # return语句创建新块并结束控制流
        return_block = self._create_block("return")
        return_block.add_statement(return_stmt)
        
        # 处理返回值表达式
        for child in return_stmt.get_children():
            self._extract_variables(child, return_block)
        
        self.cfg.add_node(return_block.id, **return_block.to_dict())
        
        if self.current_block:
            self._add_edge(self.current_block, return_block.id)
        
        return None  # return语句后无后续控制流
    
    def _process_break_stmt(self, break_stmt: Any) -> Optional[str]:
        """处理break语句"""
        break_block = self._create_block("break")
        break_block.add_statement(break_stmt)
        self.cfg.add_node(break_block.id, **break_block.to_dict())
        
        if self.current_block:
            self._add_edge(self.current_block, break_block.id)
        
        # 连接到最近的break目标
        if self.break_targets:
            self._add_edge(break_block.id, self.break_targets[-1])
        
        return None
    
    def _process_continue_stmt(self, continue_stmt: Any) -> Optional[str]:
        """处理continue语句"""
        continue_block = self._create_block("continue")
        continue_block.add_statement(continue_stmt)
        self.cfg.add_node(continue_block.id, **continue_block.to_dict())
        
        if self.current_block:
            self._add_edge(self.current_block, continue_block.id)
        
        # 连接到最近的continue目标
        if self.continue_targets:
            self._add_edge(continue_block.id, self.continue_targets[-1])
        
        return None
    
    def _process_normal_stmt(self, stmt: Any) -> Optional[str]:
        """处理普通语句"""
        if not self.current_block:
            # 创建新的基本块
            block = self._create_block("normal")
            self.cfg.add_node(block.id, **block.to_dict())
            self.current_block = block.id
        
        # 获取当前块
        current_block_data = self.cfg.nodes[self.current_block]
        block = BasicBlock(current_block_data['id'], current_block_data['type'])
        
        # 添加语句到当前块
        block.add_statement(stmt)
        self._extract_variables(stmt, block)
        
        # 更新图中的节点数据
        self.cfg.nodes[self.current_block].update(block.to_dict())
        
        return self.current_block
    
    def _extract_variables(self, node: Any, block: BasicBlock):
        """从AST节点中提取变量引用"""
        if node.kind == CursorKind.DECL_REF_EXPR:
            block.add_variable(node.spelling)
        elif node.kind == CursorKind.VAR_DECL:
            block.add_variable(node.spelling)
        
        # 递归处理子节点
        for child in node.get_children():
            self._extract_variables(child, block)
    
    def _create_block(self, block_type: str = "normal") -> BasicBlock:
        """创建新的基本块"""
        block_id = f"block_{self.block_counter}"
        self.block_counter += 1
        return BasicBlock(block_id, block_type)
    
    def _add_edge(self, from_block: str, to_block: str):
        """添加控制流边"""
        self.cfg.add_edge(from_block, to_block)
        
        # 更新前驱和后继信息
        if from_block in self.cfg.nodes:
            if 'successors' not in self.cfg.nodes[from_block]:
                self.cfg.nodes[from_block]['successors'] = set()
            self.cfg.nodes[from_block]['successors'].add(to_block)
        
        if to_block in self.cfg.nodes:
            if 'predecessors' not in self.cfg.nodes[to_block]:
                self.cfg.nodes[to_block]['predecessors'] = set()
            self.cfg.nodes[to_block]['predecessors'].add(from_block)
    
    def get_function_cfg(self, function_name: str) -> Optional[nx.DiGraph]:
        """获取指定函数的CFG"""
        return self.function_cfgs.get(function_name)
    
    def print_cfg_stats(self):
        """打印CFG统计信息"""
        for func_name, cfg in self.function_cfgs.items():
            print(f"Function: {func_name}")
            print(f"  Blocks: {cfg.number_of_nodes()}")
            print(f"  Edges: {cfg.number_of_edges()}")
            print(f"  Entry blocks: {len([n for n in cfg.nodes if cfg.nodes[n]['type'] == 'entry'])}")
            print(f"  Exit blocks: {len([n for n in cfg.nodes if cfg.nodes[n]['type'] == 'exit'])}")
            print()