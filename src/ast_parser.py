from tree_sitter import Language, Parser, Node
from src.models import (
    CategoryContext, VariableNode, FunctionNode,
    DependencyRelation, DependencyType
)
from src.logger import get_logger
import networkx as nx
from typing import Dict, List, Set


class CCodeParser:
    """C代码AST解析器"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("初始化CCodeParser")

        # 使用内置的C语言支持
        try:
            import tree_sitter_c
            self.c_lang = Language(tree_sitter_c.language())
            self.parser = Parser(self.c_lang)
            self.logger.debug("Tree-sitter C语言解析器初始化成功")
        except Exception as e:
            self.logger.error(f"Tree-sitter C语言解析器初始化失败: {e}")
            raise

    def parse(self, code: str) -> CategoryContext:
        """
        解析C代码，构建范畴上下文

        Args:
            code: C代码字符串

        Returns:
            CategoryContext: 包含函数、变量及关系的范畴上下文
        """
        self.logger.info(f"开始解析C代码，代码长度: {len(code)} 字符")

        try:
            tree = self.parser.parse(bytes(code, "utf8"))
            root_node = tree.root_node
            self.logger.debug(f"AST根节点类型: {root_node.type}")

            context = CategoryContext(variables={}, functions={}, anchors={})

            # 1. 提取函数定义
            self.logger.debug("开始遍历函数定义")
            self._traverse_functions(root_node, context)

            # 2. 提取全局变量（暂略，聚焦于函数参数及内部变量以简化演示）

            # 3. 构建调用图
            self.logger.debug("开始构建调用图")
            self._build_call_graph(context)

            self.logger.info(f"解析完成，发现 {len(context.functions)} 个函数")
            return context

        except Exception as e:
            self.logger.error(f"代码解析失败: {e}", exc_info=True)
            raise

    def _traverse_functions(self, node: Node, context: CategoryContext):
        """遍历AST，提取函数定义"""
        if node.type == "function_definition":
            # 提取函数名和返回值
            func_decl = node.child_by_field_name("declarator")
            func_name_node = func_decl.child_by_field_name("declarator")
            func_name = func_name_node.text.decode('utf8')
            return_type = node.child_by_field_name("type").text.decode('utf8')

            self.logger.debug(f"发现函数: {func_name}, 返回类型: {return_type}")

            # 提取参数
            params = []
            params_node = func_decl.child_by_field_name("parameters")
            if params_node:
                self._extract_params(params_node, params)
                self.logger.debug(f"函数 {func_name} 的参数: {params}")

            func_node = FunctionNode(
                name=func_name,
                return_type=return_type,
                parameters=params
            )
            context.functions[func_name] = func_node

            # 提取函数内变量及调用
            self._analyze_function_body(node, func_name, context)

        for child in node.children:
            self._traverse_functions(child, context)

    def _extract_params(self, node: Node, params: list):
        """提取函数参数"""
        for child in node.children:
            if child.type == "parameter_declaration":
                p_type = child.child_by_field_name("type").text.decode('utf8')
                p_decl = child.child_by_field_name("declarator")
                p_name = ""
                is_ptr = False
                is_const = "const" in p_type

                if p_decl:
                    p_name = p_decl.text.decode('utf8')
                    if p_decl.type == "pointer_declarator":
                        is_ptr = True
                        # 尝试获取指针指向的实体名
                        if p_decl.child_by_field_name("declarator"):
                            p_name = p_decl.child_by_field_name("declarator").text.decode('utf8')

                params.append({
                    "name": p_name,
                    "type": p_type,
                    "is_pointer": is_ptr,
                    "is_const": is_const
                })

    def _analyze_function_body(self, node: Node, func_name: str, context: CategoryContext):
        """分析函数体，提取变量访问、函数调用和变量依赖关系"""
        func_node = context.functions[func_name]
        call_count = 0
        var_count = 0

        # 用于追踪函数内定义的变量
        defined_vars: Set[str] = set()

        # 简单遍历函数体寻找 call_expression 和 赋值/解引用
        def traverse_body(n):
            nonlocal call_count, var_count

            # 处理赋值语句
            if n.type == "assignment_expression":
                self._extract_assignment(n, func_name, context, defined_vars)

            # 处理条件语句 (if/else)
            elif n.type == "if_statement":
                self._extract_condition(n, func_name, context, defined_vars)

            # 处理函数调用
            elif n.type == "call_expression":
                self._extract_function_call(n, func_name, context, defined_vars)
                call_count += 1

            # 处理返回语句
            elif n.type == "return_statement":
                self._extract_return(n, func_name, context, defined_vars)

            # 处理声明语句
            elif n.type == "declaration":
                self._extract_declaration(n, func_name, defined_vars)

            # 记录变量访问（简化版：识别 identifier 节点）
            if n.type == "identifier":
                var_name = n.text.decode('utf8')
                # 过滤关键字和函数名
                keywords = {"int", "void", "char", "return", "if", "else", "while", "for",
                           "float", "double", "long", "short", "unsigned", "signed", "const",
                           "static", "struct", "enum", "sizeof", "typedef"}
                if var_name not in keywords and var_name != func_name:
                    func_node.vars_accessed.append(var_name)
                    var_count += 1

            for child in n.children:
                traverse_body(child)

        body = node.child_by_field_name("body")
        if body:
            traverse_body(body)

        # 记录函数内定义的变量
        func_node.defined_vars = list(defined_vars)

        # 去重
        func_node.calls = list(set(func_node.calls))
        func_node.vars_accessed = list(set(func_node.vars_accessed))

        if func_node.calls or func_node.vars_accessed:
            self.logger.debug(
                f"函数 {func_name}: 调用 {len(func_node.calls)} 个函数, 访问 {len(func_node.vars_accessed)} 个变量, 定义 {len(defined_vars)} 个变量"
            )

    def _extract_assignment(
        self,
        node: Node,
        func_name: str,
        context: CategoryContext,
        defined_vars: Set[str]
    ):
        """提取赋值语句中的依赖关系"""
        try:
            # 赋值表达式结构: left = right
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")

            if left and right:
                left_var = self._extract_identifier(left)
                right_vars = self._extract_all_identifiers(right)

                if left_var and right_vars:
                    # 确定依赖类型
                    dep_type = DependencyType.ASSIGNMENT

                    # 检查是否是算术运算
                    if self._contains_arithmetic(right):
                        dep_type = DependencyType.ARITHMETIC

                    # 检查是否是指针解引用
                    if self._contains_pointer_dereference(right):
                        dep_type = DependencyType.POINTER

                    # 创建依赖关系
                    for right_var in right_vars:
                        if right_var != left_var:  # 避免自依赖
                            self._add_dependency(
                                context, left_var, right_var,
                                dep_type, func_name, node.start_point[0] + 1
                            )

                    # 记录左边变量为已定义（如果是新的）
                    defined_vars.add(left_var)

        except Exception as e:
            self.logger.debug(f"提取赋值关系失败: {e}")

    def _extract_condition(
        self,
        node: Node,
        func_name: str,
        context: CategoryContext,
        defined_vars: Set[str]
    ):
        """提取条件语句中的依赖关系"""
        try:
            condition = node.child_by_field_name("condition")
            if condition:
                cond_vars = self._extract_all_identifiers(condition)

                # 条件中的变量之间存在比较依赖
                if len(cond_vars) > 1:
                    for i, var1 in enumerate(cond_vars):
                        for var2 in cond_vars[i+1:]:
                            self._add_dependency(
                                context, var1, var2,
                                DependencyType.CONDITION, func_name,
                                node.start_point[0] + 1
                            )

        except Exception as e:
            self.logger.debug(f"提取条件关系失败: {e}")

    def _extract_function_call(
        self,
        node: Node,
        func_name: str,
        context: CategoryContext,
        defined_vars: Set[str]
    ):
        """提取函数调用中的依赖关系"""
        try:
            # 提取被调用函数名
            func = node.children[0]
            called_func = func.text.decode('utf8')

            func_node = context.functions.get(func_name)
            if func_node:
                func_node.calls.append(called_func)

            # 提取参数变量
            args = node.children
            for arg in args:
                if arg.type == "argument_list":
                    arg_vars = self._extract_all_identifiers(arg)
                    # 参数变量与被调用函数之间存在依赖
                    for arg_var in arg_vars:
                        if called_func in context.functions:
                            # 检查被调用函数的参数
                            for param in context.functions[called_func].parameters:
                                self._add_dependency(
                                    context, arg_var, param["name"],
                                    DependencyType.FUNCTION_CALL, func_name,
                                    node.start_point[0] + 1
                                )

        except Exception as e:
            self.logger.debug(f"提取函数调用关系失败: {e}")

    def _extract_return(
        self,
        node: Node,
        func_name: str,
        context: CategoryContext,
        defined_vars: Set[str]
    ):
        """提取返回语句中的依赖关系"""
        try:
            # 返回值可能与某些变量有依赖
            return_vars = self._extract_all_identifiers(node)
            for ret_var in return_vars:
                self._add_dependency(
                    context, func_name, ret_var,
                    DependencyType.RETURN, func_name,
                    node.start_point[0] + 1
                )
        except Exception as e:
            self.logger.debug(f"提取返回关系失败: {e}")

    def _extract_declaration(
        self,
        node: Node,
        func_name: str,
        defined_vars: Set[str]
    ):
        """提取变量声明"""
        try:
            declarator = node.child_by_field_name("declarator")
            if declarator:
                var_name = self._extract_identifier(declarator)
                if var_name:
                    defined_vars.add(var_name)
        except Exception as e:
            self.logger.debug(f"提取变量声明失败: {e}")

    def _extract_identifier(self, node: Node) -> str:
        """从节点中提取标识符名称"""
        if node.type == "identifier":
            return node.text.decode('utf8')
        for child in node.children:
            result = self._extract_identifier(child)
            if result:
                return result
        return ""

    def _extract_all_identifiers(self, node: Node) -> List[str]:
        """递归提取节点中的所有标识符"""
        identifiers = []
        keywords = {"int", "void", "char", "return", "if", "else", "while", "for",
                   "float", "double", "long", "short", "unsigned", "signed", "const"}

        def collect(n):
            if n.type == "identifier":
                name = n.text.decode('utf8')
                if name not in keywords:
                    identifiers.append(name)
            for child in n.children:
                collect(child)

        collect(node)
        return identifiers

    def _contains_arithmetic(self, node: Node) -> bool:
        """检查节点是否包含算术运算"""
        arithmetic_types = {
            "binary_expression", "unary_expression",
            "augmented_assignment_expression"
        }
        if node.type in arithmetic_types:
            return True
        for child in node.children:
            if self._contains_arithmetic(child):
                return True
        return False

    def _contains_pointer_dereference(self, node: Node) -> bool:
        """检查节点是否包含指针解引用"""
        if node.type == "pointer_expression" or "*" in node.text.decode('utf8'):
            return True
        for child in node.children:
            if self._contains_pointer_dereference(child):
                return True
        return False

    def _add_dependency(
        self,
        context: CategoryContext,
        source: str,
        target: str,
        dep_type: DependencyType,
        func_name: str,
        line_number: int
    ):
        """添加依赖关系到上下文"""
        # 添加到依赖关系列表
        rel = DependencyRelation(
            source=source,
            target=target,
            dep_type=dep_type,
            context=func_name,
            line_number=line_number
        )

        # 避免重复
        for existing in context.variable_dependencies:
            if (existing.source == source and existing.target == target and
                existing.dep_type == dep_type and existing.context == func_name):
                return

        context.variable_dependencies.append(rel)

        # 更新变量节点的依赖信息
        if source not in context.variables:
            context.variables[source] = VariableNode(
                name=source, type="unknown", is_pointer=False,
                is_const=False, scope=func_name
            )
        if target not in context.variables:
            context.variables[target] = VariableNode(
                name=target, type="unknown", is_pointer=False,
                is_const=False, scope=func_name
            )

        # 更新depends_on和dependents
        if dep_type not in context.variables[source].depends_on:
            context.variables[source].depends_on[target] = set()
        context.variables[source].depends_on[target].add(dep_type)

        if dep_type not in context.variables[target].dependents:
            context.variables[target].dependents[source] = set()
        context.variables[target].dependents[source].add(dep_type)

    def _build_call_graph(self, context: CategoryContext):
        """构建函数调用图（态射关系）"""
        relation_count = 0

        # 构建双向依赖（态射关系）
        for fname, fnode in context.functions.items():
            for called_name in fnode.calls:
                if called_name in context.functions:
                    context.functions[called_name].called_by.append(fname)
                    # 添加到函数调用关系列表
                    context.function_calls.append((fname, called_name))
                    relation_count += 1
                    self.logger.debug(f"调用关系: {fname} -> {called_name}")

        self.logger.info(f"构建调用图完成，共 {relation_count} 条调用关系")
