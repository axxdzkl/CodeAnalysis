"""
可视化模块 - 基于Plotly的3D交互式可视化

本模块实现了大规模代码分析结果的可视化功能，包括：
- 3D交互式CFG可视化
- 3D程序依赖图(PDG)可视化 
- 多层次调用图可视化
- 动态耦合度热力图
- 大规模数据优化展示
- HTML报告生成
- 实时交互式仪表板
"""

import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from typing import Dict, Any, Optional, List, Tuple, Set
import logging
import os
import json
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
import dash
from dash import dcc, html, Input, Output, callback
import threading
import webbrowser
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class AdvancedGraphVisualizer:
    """
    高级图可视化器 - 使用Plotly实现3D交互式可视化
    支持大规模代码仓库(>1000节点, >10000条边)
    """
    
    def __init__(self):
        self.output_dir = "analysis_output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 性能优化参数
        self.max_nodes_3d = 2000  # 3D显示最大节点数
        self.max_edges_3d = 15000  # 3D显示最大边数
        self.sampling_threshold = 1000  # 采样阈值
        
        # 颜色配置
        self.color_schemes = {
            'node_types': {
                'entry': '#2E8B57',      # 海绿色
                'exit': '#DC143C',       # 深红色  
                'return': '#FF6347',     # 番茄色
                'condition': '#FFD700',  # 金色
                'normal': '#4169E1',     # 皇家蓝
                'loop': '#9370DB',       # 中紫罗兰色
                'function': '#FF4500',   # 橙红色
            },
            'edge_types': {
                'control': '#808080',    # 灰色
                'data': '#0000FF',       # 蓝色
                'call': '#FF0000',       # 红色
                'interprocedural': '#800080'  # 紫色
            },
            'coupling_levels': {
                'low': '#00FF00',        # 绿色
                'medium': '#FFFF00',     # 黄色
                'high': '#FF6600',       # 橙色
                'very_high': '#FF0000'   # 红色
            }
        }
    
    def _optimize_large_graph(self, graph: nx.DiGraph, max_nodes: int = None, 
                             preserve_important: bool = True) -> nx.DiGraph:
        """
        优化大规模图的显示
        使用智能采样和节点聚类技术
        """
        if max_nodes is None:
            max_nodes = self.max_nodes_3d
            
        if graph.number_of_nodes() <= max_nodes:
            return graph
            
        logger.info(f"Optimizing large graph: {graph.number_of_nodes()} nodes -> {max_nodes} nodes")
        
        # 计算节点重要性分数
        importance_scores = {}
        
        # 基于度数的重要性
        for node in graph.nodes():
            in_degree = graph.in_degree(node)
            out_degree = graph.out_degree(node)
            betweenness = 0
            
            # 计算中介中心性(仅对小规模子集)
            if graph.number_of_nodes() < 500:
                try:
                    centrality = nx.betweenness_centrality(graph)
                    betweenness = centrality.get(node, 0)
                except:
                    pass
            
            # 综合评分
            importance_scores[node] = (
                in_degree * 2 +      # 被调用次数
                out_degree * 1.5 +   # 调用其他函数次数
                betweenness * 100    # 中介中心性
            )
        
        # 保留重要节点
        important_nodes = set()
        
        if preserve_important:
            # 保留入口和出口节点
            for node in graph.nodes():
                node_data = graph.nodes[node]
                if node_data.get('type') in ['entry', 'exit', 'return']:
                    important_nodes.add(node)
            
            # 保留高度数节点
            degree_threshold = np.percentile(list(dict(graph.degree()).values()), 90)
            for node in graph.nodes():
                if graph.degree(node) >= degree_threshold:
                    important_nodes.add(node)
        
        # 选择最重要的节点
        remaining_budget = max_nodes - len(important_nodes)
        if remaining_budget > 0:
            sorted_nodes = sorted(
                [(node, score) for node, score in importance_scores.items() 
                 if node not in important_nodes],
                key=lambda x: x[1], reverse=True
            )
            selected_nodes = [node for node, _ in sorted_nodes[:remaining_budget]]
            important_nodes.update(selected_nodes)
        
        # 创建子图
        subgraph = graph.subgraph(important_nodes).copy()
        
        logger.info(f"Graph optimization completed: {subgraph.number_of_nodes()} nodes, "
                   f"{subgraph.number_of_edges()} edges")
        
        return subgraph
    
    def _calculate_3d_layout(self, graph: nx.DiGraph, algorithm: str = 'force_directed') -> Dict[str, Tuple[float, float, float]]:
        """
        计算3D布局坐标
        支持多种布局算法
        """
        logger.info(f"Calculating 3D layout using {algorithm} algorithm...")
        
        pos_3d = {}
        
        if algorithm == 'force_directed':
            # 使用spring layout然后扩展到3D
            try:
                pos_2d = nx.spring_layout(graph, k=3, iterations=100)
                
                # 添加Z维度，基于节点层次结构
                try:
                    # 计算层次结构
                    if nx.is_directed_acyclic_graph(graph):
                        layers = list(nx.topological_generations(graph))
                        node_layers = {}
                        for i, layer in enumerate(layers):
                            for node in layer:
                                node_layers[node] = i
                    else:
                        # 如果不是DAG，使用随机分层
                        node_layers = {node: np.random.random() for node in graph.nodes()}
                    
                    max_layer = max(node_layers.values()) if node_layers else 1
                    
                    for node, (x, y) in pos_2d.items():
                        layer = node_layers.get(node, 0)
                        z = (layer / max_layer) * 2 - 1  # 正规化到[-1, 1]
                        pos_3d[node] = (x, y, z)
                        
                except Exception:
                    # 如果层次计算失败，使用随机Z坐标
                    for node, (x, y) in pos_2d.items():
                        z = np.random.uniform(-1, 1)
                        pos_3d[node] = (x, y, z)
                        
            except Exception as e:
                logger.warning(f"Force-directed layout failed: {e}, using random layout")
                algorithm = 'random'
        
        if algorithm == 'random' or not pos_3d:
            # 随机布局
            for node in graph.nodes():
                pos_3d[node] = (
                    np.random.uniform(-1, 1),
                    np.random.uniform(-1, 1), 
                    np.random.uniform(-1, 1)
                )
        
        elif algorithm == 'hierarchical':
            # 分层布局
            try:
                if nx.is_directed_acyclic_graph(graph):
                    layers = list(nx.topological_generations(graph))
                    
                    for layer_idx, layer in enumerate(layers):
                        z = layer_idx / (len(layers) - 1) if len(layers) > 1 else 0
                        layer_nodes = list(layer)
                        
                        # 在每一层内使用圆形布局
                        n_nodes = len(layer_nodes)
                        for i, node in enumerate(layer_nodes):
                            angle = 2 * np.pi * i / n_nodes if n_nodes > 1 else 0
                            radius = min(1.0, n_nodes * 0.1)
                            
                            x = radius * np.cos(angle)
                            y = radius * np.sin(angle)
                            pos_3d[node] = (x, y, z)
                else:
                    # 如果不是DAG，回退到随机布局
                    algorithm = 'random'
                    for node in graph.nodes():
                        pos_3d[node] = (
                            np.random.uniform(-1, 1),
                            np.random.uniform(-1, 1),
                            np.random.uniform(-1, 1)
                        )
                        
            except Exception as e:
                logger.warning(f"Hierarchical layout failed: {e}, using random layout")
                for node in graph.nodes():
                    pos_3d[node] = (
                        np.random.uniform(-1, 1),
                        np.random.uniform(-1, 1),
                        np.random.uniform(-1, 1)
                    )
        
        logger.info(f"3D layout calculation completed for {len(pos_3d)} nodes")
        return pos_3d
    
    def visualize_3d_cfg(self, cfg: nx.DiGraph, func_name: str, 
                         interactive: bool = True) -> str:
        """
        可视化3D控制流图
        支持大规模CFG的交互式展示
        """
        logger.info(f"Creating 3D CFG visualization for function: {func_name}")
        
        # 优化大图
        optimized_cfg = self._optimize_large_graph(cfg, self.max_nodes_3d)
        
        # 计算3D布局
        pos_3d = self._calculate_3d_layout(optimized_cfg, 'hierarchical')
        
        # 准备节点数据
        node_x = []
        node_y = []
        node_z = []
        node_colors = []
        node_texts = []
        node_sizes = []
        
        for node in optimized_cfg.nodes():
            x, y, z = pos_3d[node]
            node_x.append(x)
            node_y.append(y)
            node_z.append(z)
            
            # 设置节点颜色
            node_data = optimized_cfg.nodes[node]
            node_type = node_data.get('type', 'normal')
            node_colors.append(self.color_schemes['node_types'].get(node_type, '#4169E1'))
            
            # 设置节点大小（基于度数）
            degree = optimized_cfg.degree(node)
            size = max(5, min(20, degree * 2 + 8))
            node_sizes.append(size)
            
            # 节点信息
            statements = node_data.get('statements', [])
            stmt_text = '<br>'.join(statements[:3])  # 仅显示前3条语句
            if len(statements) > 3:
                stmt_text += f'<br>... (+{len(statements)-3} more)'
            
            node_texts.append(
                f"Node: {node}<br>"
                f"Type: {node_type}<br>"
                f"Degree: {degree}<br>"
                f"Statements:<br>{stmt_text}"
            )
        
        # 准备边数据
        edge_x = []
        edge_y = []
        edge_z = []
        edge_colors = []
        
        for edge in optimized_cfg.edges():
            x0, y0, z0 = pos_3d[edge[0]]
            x1, y1, z1 = pos_3d[edge[1]]
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_z.extend([z0, z1, None])
            
            # 边颜色
            edge_data = optimized_cfg.edges[edge]
            edge_type = edge_data.get('type', 'control')
            edge_colors.append(self.color_schemes['edge_types'].get(edge_type, '#808080'))
        
        # 创建3D散点图
        node_trace = go.Scatter3d(
            x=node_x, y=node_y, z=node_z,
            mode='markers+text',
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=2, color='black'),
                opacity=0.8
            ),
            text=[str(node) for node in optimized_cfg.nodes()],
            textposition='middle center',
            hovertext=node_texts,
            hoverinfo='text',
            name='Nodes'
        )
        
        # 创建边迹踪
        edge_trace = go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(width=2, color='rgba(128,128,128,0.6)'),
            hoverinfo='none',
            name='Edges'
        )
        
        # 创建图形
        fig = go.Figure(data=[edge_trace, node_trace])
        
        fig.update_layout(
            title=dict(
                text=f'3D Control Flow Graph: {func_name}<br>' +
                     f'<sub>Nodes: {optimized_cfg.number_of_nodes()}, ' +
                     f'Edges: {optimized_cfg.number_of_edges()}</sub>',
                x=0.5
            ),
            scene=dict(
                xaxis=dict(showbackground=True, backgroundcolor='rgba(230,230,230,0.3)'),
                yaxis=dict(showbackground=True, backgroundcolor='rgba(230,230,230,0.3)'),
                zaxis=dict(showbackground=True, backgroundcolor='rgba(230,230,230,0.3)'),
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                )
            ),
            width=1200,
            height=800,
            showlegend=True,
            legend=dict(x=0, y=1),
            margin=dict(l=0, r=0, b=0, t=60)
        )
        
        # 保存文件
        output_path = os.path.join(self.output_dir, f'3d_cfg_{func_name}.html')
        
        if interactive:
            fig.write_html(output_path, include_plotlyjs='cdn')
        else:
            # 静态图像
            static_path = os.path.join(self.output_dir, f'3d_cfg_{func_name}.png')
            try:
                fig.write_image(static_path, width=1200, height=800, scale=2)
            except Exception as e:
                logger.warning(f"Could not save static image: {e}")
        
        logger.info(f"3D CFG visualization saved to: {output_path}")
        return output_path
    
    def visualize_3d_call_graph(self, call_graph: nx.DiGraph, 
                                highlight_cycles: bool = True) -> str:
        """
        可视化3D函数调用图
        支持大规模调用关系的分层展示
        """
        logger.info("Creating 3D call graph visualization...")
        
        # 优化大图
        optimized_graph = self._optimize_large_graph(call_graph, self.max_nodes_3d, True)
        
        # 检测循环
        cycles = []
        if highlight_cycles:
            try:
                cycles = list(nx.simple_cycles(optimized_graph))
            except Exception as e:
                logger.warning(f"Cycle detection failed: {e}")
        
        # 使用分层布局
        pos_3d = self._calculate_3d_layout(optimized_graph, 'hierarchical')
        
        # 准备节点数据
        node_x, node_y, node_z = [], [], []
        node_colors, node_texts, node_sizes = [], [], []
        
        # 计算节点指标
        in_degrees = dict(optimized_graph.in_degree())
        out_degrees = dict(optimized_graph.out_degree())
        
        # 识别循环中的节点
        cycle_nodes = set()
        for cycle in cycles:
            cycle_nodes.update(cycle)
        
        for node in optimized_graph.nodes():
            x, y, z = pos_3d[node]
            node_x.append(x)
            node_y.append(y) 
            node_z.append(z)
            
            # 设置节点颜色
            node_data = optimized_graph.nodes[node]
            is_recursive = node_data.get('is_recursive', False)
            
            if node in cycle_nodes:
                color = '#FF0000'  # 红色表示循环
            elif is_recursive:
                color = '#FF6347'  # 番茄红表示递归
            else:
                # 基于调用次数的颜色渐变
                in_degree = in_degrees[node]
                max_in_degree = max(in_degrees.values()) if in_degrees.values() else 1
                intensity = min(1.0, in_degree / max_in_degree)
                color = f'rgba(65, 105, 225, {0.3 + 0.7 * intensity})'  # 蓝色渐变
            
            node_colors.append(color)
            
            # 设置节点大小
            total_degree = in_degrees[node] + out_degrees[node]
            size = max(8, min(25, total_degree * 1.5 + 10))
            node_sizes.append(size)
            
            # 节点信息
            node_texts.append(
                f"Function: {node}<br>"
                f"Called by: {in_degrees[node]} functions<br>"
                f"Calls: {out_degrees[node]} functions<br>"
                f"Recursive: {'Yes' if is_recursive else 'No'}<br>"
                f"In cycle: {'Yes' if node in cycle_nodes else 'No'}"
            )
        
        # 准备边数据
        edge_x, edge_y, edge_z = [], [], []
        edge_info = []
        
        for edge in optimized_graph.edges(data=True):
            src, dst, data = edge
            x0, y0, z0 = pos_3d[src]
            x1, y1, z1 = pos_3d[dst]
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_z.extend([z0, z1, None])
            
            # 边信息
            call_count = data.get('call_count', 1)
            edge_info.append(f"{src} → {dst} (calls: {call_count})")
        
        # 创建3D散点图
        node_trace = go.Scatter3d(
            x=node_x, y=node_y, z=node_z,
            mode='markers+text',
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=1, color='black'),
                opacity=0.8
            ),
            text=[str(node)[:10] for node in optimized_graph.nodes()],  # 截断长函数名
            textposition='middle center',
            textfont=dict(size=8),
            hovertext=node_texts,
            hoverinfo='text',
            name='Functions'
        )
        
        # 创建边迹踪
        edge_trace = go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(width=1, color='rgba(100,100,100,0.5)'),
            hoverinfo='none',
            name='Calls'
        )
        
        # 高亮循环边
        cycle_traces = []
        if cycles and highlight_cycles:
            for i, cycle in enumerate(cycles[:5]):  # 最多显示5个循环
                cycle_x, cycle_y, cycle_z = [], [], []
                
                for j in range(len(cycle)):
                    src = cycle[j]
                    dst = cycle[(j + 1) % len(cycle)]
                    
                    if src in pos_3d and dst in pos_3d:
                        x0, y0, z0 = pos_3d[src]
                        x1, y1, z1 = pos_3d[dst]
                        
                        cycle_x.extend([x0, x1, None])
                        cycle_y.extend([y0, y1, None])
                        cycle_z.extend([z0, z1, None])
                
                if cycle_x:  # 确保有数据
                    cycle_trace = go.Scatter3d(
                        x=cycle_x, y=cycle_y, z=cycle_z,
                        mode='lines',
                        line=dict(width=4, color=f'rgba(255,{50*i},{50*i},0.8)'),
                        name=f'Cycle {i+1}',
                        hoverinfo='name'
                    )
                    cycle_traces.append(cycle_trace)
        
        # 组合所有迹踪
        traces = [edge_trace, node_trace] + cycle_traces
        
        # 创建图形
        fig = go.Figure(data=traces)
        
        fig.update_layout(
            title=dict(
                text=f'3D Function Call Graph<br>' +
                     f'<sub>Functions: {optimized_graph.number_of_nodes()}, ' +
                     f'Calls: {optimized_graph.number_of_edges()}, ' +
                     f'Cycles: {len(cycles)}</sub>',
                x=0.5
            ),
            scene=dict(
                xaxis=dict(showbackground=True, backgroundcolor='rgba(230,230,230,0.3)'),
                yaxis=dict(showbackground=True, backgroundcolor='rgba(230,230,230,0.3)'),
                zaxis=dict(showbackground=True, backgroundcolor='rgba(230,230,230,0.3)'),
                camera=dict(eye=dict(x=2, y=2, z=2))
            ),
            width=1400,
            height=900,
            showlegend=True
        )
        
        # 保存文件
        output_path = os.path.join(self.output_dir, '3d_call_graph.html')
        fig.write_html(output_path, include_plotlyjs='cdn')
        
        logger.info(f"3D call graph saved to: {output_path}")
        return output_path
    
    def visualize_interactive_coupling_heatmap(self, coupling_data: Dict[str, Any], 
                                             function_names: List[str]) -> str:
        """
        创建交互式耦合度热力图
        支持大规模函数矩阵的动态缩放和筛选
        """
        logger.info("Creating interactive coupling heatmap...")
        
        # 准备数据
        metrics = coupling_data.get('metrics', {})
        
        # 构建耦合度矩阵
        n = len(function_names)
        coupling_matrix = np.zeros((n, n))
        coupling_details = np.empty((n, n), dtype=object)
        
        name_to_index = {name: i for i, name in enumerate(function_names)}
        
        for i, func1 in enumerate(function_names):
            for j, func2 in enumerate(function_names):
                if func1 in metrics and func2 in metrics:
                    # 计算相互耦合度
                    m1 = metrics[func1]
                    m2 = metrics[func2]
                    
                    if i == j:
                        # 对角线上显示自身复杂度
                        coupling = (m1.data_coupling + m1.control_coupling + 
                                  m1.parameter_coupling + m1.global_coupling)
                    else:
                        # 计算两个函数之间的耦合度
                        shared_globals = len(set(getattr(m1, 'global_vars', [])) & 
                                           set(getattr(m2, 'global_vars', [])))
                        coupling = shared_globals * 2
                    
                    coupling_matrix[i][j] = coupling
                    
                    # 详细信息
                    coupling_details[i][j] = {
                        'source': func1,
                        'target': func2,
                        'coupling': coupling,
                        'data_coupling': getattr(m1, 'data_coupling', 0),
                        'control_coupling': getattr(m1, 'control_coupling', 0),
                        'parameter_coupling': getattr(m1, 'parameter_coupling', 0),
                        'global_coupling': getattr(m1, 'global_coupling', 0)
                    }
        
        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=coupling_matrix,
            x=function_names,
            y=function_names,
            colorscale='YlOrRd',
            hoverongaps=False,
            hovertemplate=
                '<b>%{x}</b> → <b>%{y}</b><br>' +
                'Coupling: %{z:.1f}<br>' +
                '<extra></extra>'
        ))
        
        # 添加数值标注（仅在较小矩阵中）
        if n <= 50:
            annotations = []
            for i in range(n):
                for j in range(n):
                    if coupling_matrix[i][j] > 0:
                        annotations.append(
                            dict(
                                x=function_names[j],
                                y=function_names[i],
                                text=f'{coupling_matrix[i][j]:.1f}',
                                showarrow=False,
                                font=dict(
                                    color='white' if coupling_matrix[i][j] > np.max(coupling_matrix)/2 else 'black',
                                    size=8
                                )
                            )
                        )
            fig.update_layout(annotations=annotations)
        
        fig.update_layout(
            title=dict(
                text=f'Interactive Function Coupling Heatmap<br>' +
                     f'<sub>{n} functions, Max coupling: {np.max(coupling_matrix):.1f}</sub>',
                x=0.5
            ),
            xaxis_title='Target Function',
            yaxis_title='Source Function',
            width=max(800, n * 15),
            height=max(600, n * 15)
        )
        
        # 保存文件
        output_path = os.path.join(self.output_dir, 'interactive_coupling_heatmap.html')
        fig.write_html(output_path, include_plotlyjs='cdn')
        
        logger.info(f"Interactive coupling heatmap saved to: {output_path}")
        return output_path
    
    def create_dashboard(self, analysis_results: Dict[str, Any], port: int = 8050) -> str:
        """
        创建实时交互式仪表板
        集成所有分析结果的综合展示
        """
        logger.info("Creating interactive dashboard...")
        
        # 初始化Dash应用
        app = dash.Dash(__name__)
        
        # 获取数据
        cfgs = analysis_results.get('cfgs', {})
        call_graph = analysis_results.get('call_graph')
        coupling_data = analysis_results.get('coupling', {})
        
        # 准备选项
        function_options = [{'label': func, 'value': func} for func in cfgs.keys()]
        
        # 布局
        app.layout = html.Div([
            html.H1("📈 C代码静态分析仪表板", 
                   style={'textAlign': 'center', 'marginBottom': '30px'}),
            
            # 控制面板
            html.Div([
                html.Div([
                    html.Label("选择函数:"),
                    dcc.Dropdown(
                        id='function-dropdown',
                        options=function_options,
                        value=list(cfgs.keys())[0] if cfgs else None,
                        style={'marginBottom': '10px'}
                    )
                ], style={'width': '30%', 'display': 'inline-block'}),
                
                html.Div([
                    html.Label("可视化类型:"),
                    dcc.RadioItems(
                        id='viz-type',
                        options=[
                            {'label': 'CFG', 'value': 'cfg'},
                            {'label': '调用图', 'value': 'callgraph'},
                            {'label': '耦合度', 'value': 'coupling'}
                        ],
                        value='cfg',
                        inline=True
                    )
                ], style={'width': '40%', 'display': 'inline-block'}),
                
                html.Div([
                    html.Button('刷新', id='refresh-btn', n_clicks=0,
                               style={'padding': '10px 20px'})
                ], style={'width': '30%', 'display': 'inline-block', 'textAlign': 'right'})
                
            ], style={'marginBottom': '30px', 'padding': '20px', 
                     'backgroundColor': '#f0f0f0', 'borderRadius': '10px'}),
            
            # 统计信息
            html.Div(id='stats-panel', 
                    style={'marginBottom': '20px', 'padding': '15px',
                          'backgroundColor': '#e8f4fd', 'borderRadius': '10px'}),
            
            # 主要可视化区域
            html.Div([
                dcc.Graph(id='main-graph', style={'height': '600px'})
            ]),
            
            # 辅助信息
            html.Div(id='detail-panel',
                    style={'marginTop': '20px', 'padding': '15px',
                          'backgroundColor': '#f8f9fa', 'borderRadius': '10px'})
        ], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif'})
        
        # 回调函数
        @app.callback(
            [Output('main-graph', 'figure'),
             Output('stats-panel', 'children'),
             Output('detail-panel', 'children')],
            [Input('function-dropdown', 'value'),
             Input('viz-type', 'value'),
             Input('refresh-btn', 'n_clicks')]
        )
        def update_dashboard(selected_function, viz_type, n_clicks):
            # 统计信息
            total_functions = len(cfgs)
            total_nodes = sum(cfg.number_of_nodes() for cfg in cfgs.values())
            total_edges = sum(cfg.number_of_edges() for cfg in cfgs.values())
            
            stats = html.Div([
                html.H3("📈 系统统计"),
                html.P(f"函数数量: {total_functions} | 节点数: {total_nodes} | 边数: {total_edges}")
            ])
            
            # 主图
            if viz_type == 'cfg' and selected_function in cfgs:
                cfg = cfgs[selected_function]
                # 使用简化的2D布局显示
                pos = nx.spring_layout(cfg)
                
                edge_x, edge_y = [], []
                for edge in cfg.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
                
                node_x = [pos[node][0] for node in cfg.nodes()]
                node_y = [pos[node][1] for node in cfg.nodes()]
                
                fig = go.Figure()
                
                # 边
                fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines',
                                        line=dict(width=1, color='gray'),
                                        hoverinfo='none', showlegend=False))
                
                # 节点
                fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text',
                                        marker=dict(size=10, color='lightblue'),
                                        text=list(cfg.nodes()),
                                        textposition='middle center',
                                        showlegend=False))
                
                fig.update_layout(title=f'CFG: {selected_function}',
                                 showlegend=False, height=600)
                
                detail = html.Div([
                    html.H4(f"🔍 {selected_function} 详情"),
                    html.P(f"基本块数: {cfg.number_of_nodes()}"),
                    html.P(f"边数: {cfg.number_of_edges()}")
                ])
                
            elif viz_type == 'callgraph' and call_graph:
                # 简化调用图显示
                pos = nx.spring_layout(call_graph)
                
                edge_x, edge_y = [], []
                for edge in call_graph.edges():
                    if edge[0] in pos and edge[1] in pos:
                        x0, y0 = pos[edge[0]]
                        x1, y1 = pos[edge[1]]
                        edge_x.extend([x0, x1, None])
                        edge_y.extend([y0, y1, None])
                
                node_x = [pos[node][0] for node in call_graph.nodes() if node in pos]
                node_y = [pos[node][1] for node in call_graph.nodes() if node in pos]
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines',
                                        line=dict(width=1, color='gray'),
                                        hoverinfo='none', showlegend=False))
                
                fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers',
                                        marker=dict(size=8, color='orange'),
                                        text=[node for node in call_graph.nodes() if node in pos],
                                        showlegend=False))
                
                fig.update_layout(title='函数调用图', showlegend=False, height=600)
                
                detail = html.Div([
                    html.H4("🔗 调用图统计"),
                    html.P(f"函数数: {call_graph.number_of_nodes()}"),
                    html.P(f"调用关系: {call_graph.number_of_edges()}")
                ])
                
            else:
                # 默认显示
                fig = go.Figure()
                fig.add_annotation(text="请选择有效的可视化选项",
                                 xref="paper", yref="paper",
                                 x=0.5, y=0.5, showarrow=False)
                fig.update_layout(height=600)
                detail = html.Div()
            
            return fig, stats, detail
        
        # 在新线程中启动服务器
        def run_server():
            try:
                app.run_server(debug=False, host='127.0.0.1', port=port)
            except Exception as e:
                logger.error(f"Dashboard server error: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # 稍等一下然后打开浏览器
        import time
        time.sleep(2)
        
        dashboard_url = f'http://127.0.0.1:{port}'
        try:
            webbrowser.open(dashboard_url)
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")
        

class SourceMapper:
    """
    增强的源码映射器
    支持大规模项目的报告生成
    """
    
    def __init__(self, tu: Any):
        self.tu = tu
        self.source_map: Dict[str, Any] = {}
    
    def build_source_map(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """构建源码映射"""
        logger.info("Building source map...")
        
        # 映射CFG节点到源码位置
        cfgs = analysis_results.get('cfgs', {})
        for func_name, cfg in cfgs.items():
            for block_id, block_data in cfg.nodes(data=True):
                location = block_data.get('location')
                if location:
                    self.source_map[block_id] = {
                        'file': location.file.name if hasattr(location, 'file') else 'unknown',
                        'line': location.line if hasattr(location, 'line') else 0,
                        'column': location.column if hasattr(location, 'column') else 0,
                        'function': func_name
                    }
        
        # 映射PDG节点到源码位置
        pdgs = analysis_results.get('pdgs', {})
        for func_name, pdg in pdgs.items():
            for node_id, node_data in pdg.nodes(data=True):
                location = node_data.get('location')
                if location and node_id not in self.source_map:
                    self.source_map[node_id] = {
                        'file': location.file.name if hasattr(location, 'file') else 'unknown',
                        'line': location.line if hasattr(location, 'line') else 0,
                        'column': location.column if hasattr(location, 'column') else 0,
                        'function': func_name
                    }
        
        return self.source_map
        
    def generate_enhanced_html_report(self, analysis_results: Dict[str, Any]) -> str:
        """
        生成增强的HTML报告，集成Plotly交互式可视化
        """
        logger.info("Generating enhanced HTML report with interactive visualizations...")
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>C静态分析报告 - 增强版</title>
            <meta charset="utf-8">
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0; padding: 20px; background-color: #f8f9fa;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 30px; border-radius: 15px;
                    text-align: center; margin-bottom: 30px;
                }
                .section {
                    background: white; margin: 20px 0; padding: 25px;
                    border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .metrics-grid {
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px; margin: 20px 0;
                }
                .metric-card {
                    background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%);
                    color: white; padding: 20px; border-radius: 10px;
                    text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                }
                .metric-value {
                    font-size: 2.5em; font-weight: bold; margin-bottom: 5px;
                }
                .metric-label {
                    font-size: 0.9em; opacity: 0.9;
                }
                .viz-container {
                    margin: 20px 0; min-height: 400px;
                    border: 1px solid #dee2e6; border-radius: 8px;
                }
                .tab-container {
                    display: flex; margin-bottom: 20px;
                }
                .tab {
                    padding: 12px 24px; background: #e9ecef;
                    border: none; border-radius: 8px 8px 0 0;
                    cursor: pointer; margin-right: 5px;
                    transition: background 0.3s;
                }
                .tab.active {
                    background: #007bff; color: white;
                }
                .tab-content {
                    display: none; padding: 20px;
                }
                .tab-content.active {
                    display: block;
                }
                table {
                    width: 100%; border-collapse: collapse; margin: 15px 0;
                }
                th, td {
                    padding: 12px; text-align: left;
                    border-bottom: 1px solid #dee2e6;
                }
                th {
                    background: #f8f9fa; font-weight: 600;
                }
                .high-coupling { background-color: #fee; }
                .medium-coupling { background-color: #fff3cd; }
                .low-coupling { background-color: #e7f5e7; }
                .progress-bar {
                    height: 20px; background: #e9ecef;
                    border-radius: 10px; overflow: hidden;
                }
                .progress-fill {
                    height: 100%; background: linear-gradient(90deg, #28a745, #ffc107, #dc3545);
                    transition: width 0.3s;
                }
                .alert {
                    padding: 15px; margin: 15px 0;
                    border-radius: 8px; border-left: 4px solid;
                }
                .alert-info { background: #e3f2fd; border-color: #2196f3; }
                .alert-warning { background: #fff8e1; border-color: #ff9800; }
                .alert-success { background: #e8f5e8; border-color: #4caf50; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📈 C语言静态分析报告 - 增强版</h1>
                <p>🗓️ 生成时间: {timestamp} | 📁 分析文件: {source_file}</p>
                <p>🔍 交互式大规模数据可视化 | 🚀 支持>1000节点</p>
            </div>
            
            <div class="section">
                <h2>📈 分析概览</h2>
                <div class="metrics-grid">
                    {overview_metrics}
                </div>
                {performance_alert}
            </div>
            
            <div class="section">
                <h2>🎯 交互式可视化</h2>
                <div class="tab-container">
                    <button class="tab active" onclick="showTab('cfg')">CFG 分析</button>
                    <button class="tab" onclick="showTab('callgraph')">调用图</button>
                    <button class="tab" onclick="showTab('coupling')">耦合度</button>
                    <button class="tab" onclick="showTab('metrics')">指标分析</button>
                </div>
                
                <div id="cfg" class="tab-content active">
                    <div class="viz-container" id="cfg-viz"></div>
                </div>
                
                <div id="callgraph" class="tab-content">
                    <div class="viz-container" id="callgraph-viz"></div>
                </div>
                
                <div id="coupling" class="tab-content">
                    <div class="viz-container" id="coupling-viz"></div>
                </div>
                
                <div id="metrics" class="tab-content">
                    {metrics_analysis}
                </div>
            </div>
            
            <div class="section">
                <h2>📄 详细统计</h2>
                {detailed_stats}
            </div>
            
            <div class="section">
                <h2>💡 优化建议</h2>
                {optimization_suggestions}
            </div>
            
            <script>
                function showTab(tabName) {
                    // 隐藏所有标签页
                    var contents = document.querySelectorAll('.tab-content');
                    contents.forEach(content => content.classList.remove('active'));
                    
                    var tabs = document.querySelectorAll('.tab');
                    tabs.forEach(tab => tab.classList.remove('active'));
                    
                    // 显示选中的标签页
                    document.getElementById(tabName).classList.add('active');
                    event.target.classList.add('active');
                }
                
                // 初始化可视化
                {plotly_scripts}
            </script>
        </body>
        </html>
        """
        
        # 生成内容
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        source_file = getattr(self.tu, 'spelling', 'Unknown')
        
        overview_metrics = self._generate_enhanced_overview_metrics(analysis_results)
        performance_alert = self._generate_performance_alert(analysis_results)
        metrics_analysis = self._generate_metrics_analysis(analysis_results)
        detailed_stats = self._generate_detailed_stats(analysis_results)
        optimization_suggestions = self._generate_enhanced_optimization_suggestions(analysis_results)
        plotly_scripts = self._generate_plotly_scripts(analysis_results)
        
    def _generate_plotly_scripts(self, results: Dict[str, Any]) -> str:
        """生成Plotly交互式图表的JavaScript代码"""
        scripts = []
        
        # CFG简化显示
        cfgs = results.get('cfgs', {})
        if cfgs:
            sample_func = next(iter(cfgs.keys()))
            cfg = cfgs[sample_func]
            
            try:
                pos = nx.spring_layout(cfg)
                node_x = [pos[node][0] for node in cfg.nodes()]
                node_y = [pos[node][1] for node in cfg.nodes()]
                node_text = list(cfg.nodes())
                
                edge_x, edge_y = [], []
                for edge in cfg.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
                
                cfg_script = f"""
                Plotly.newPlot('cfg-viz', [
                    {{x: {edge_x}, y: {edge_y}, mode: 'lines', line: {{color: 'gray'}}, hoverinfo: 'none'}},
                    {{x: {node_x}, y: {node_y}, mode: 'markers+text', 
                      marker: {{size: 10, color: 'lightblue'}}, text: {node_text}}}
                ], {{title: 'CFG: {sample_func}', showlegend: false}});
                """
                scripts.append(cfg_script)
            except Exception as e:
                logger.warning(f"CFG script error: {e}")
        
        return '\n'.join(scripts)


# 保留原有的GraphVisualizer作为备用
class GraphVisualizer:
    """原有图可视化器(使用matplotlib)"""
    
    def __init__(self):
        self.output_dir = "analysis_output"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def visualize_cfg(self, cfg: nx.DiGraph, func_name: str) -> str:
        """可视化控制流图(传统方式)"""
        try:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(12, 8))
            plt.title(f"Control Flow Graph - {func_name}")
            
            node_colors = []
            for node in cfg.nodes():
                node_data = cfg.nodes[node]
                node_type = node_data.get('type', 'normal')
                
                if node_type == 'entry':
                    node_colors.append('lightgreen')
                elif node_type in ['exit', 'return']:
                    node_colors.append('lightcoral')
                elif node_type == 'condition':
                    node_colors.append('lightyellow')
                else:
                    node_colors.append('lightblue')
            
            pos = nx.spring_layout(cfg, k=2, iterations=50)
            nx.draw(cfg, pos, 
                   node_color=node_colors,
                   node_size=1500,
                   font_size=8,
                   font_weight='bold',
                   arrows=True,
                   edge_color='gray',
                   with_labels=True)
            
            output_path = os.path.join(self.output_dir, f"cfg_{func_name}.png")
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"CFG saved to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error visualizing CFG: {e}")
            return ""
    
    def visualize_call_graph(self, call_graph: nx.DiGraph) -> str:
        """可视化函数调用图(传统方式)"""
        try:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(15, 10))
            plt.title("Function Call Graph")
            
            node_sizes = []
            for node in call_graph.nodes():
                in_degree = call_graph.in_degree(node)
                size = max(300, in_degree * 100)
                node_sizes.append(size)
            
            node_colors = []
            for node in call_graph.nodes():
                is_recursive = call_graph.nodes[node].get('is_recursive', False)
                if is_recursive:
                    node_colors.append('red')
                else:
                    node_colors.append('lightblue')
            
            pos = nx.spring_layout(call_graph, k=3, iterations=50)
            nx.draw(call_graph, pos,
                   node_color=node_colors,
                   node_size=node_sizes,
                   font_size=6,
                   arrows=True,
                   edge_color='gray',
                   with_labels=True)
            
            output_path = os.path.join(self.output_dir, "call_graph.png")
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Call graph saved to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error visualizing call graph: {e}")
            return ""
    
    def generate_html_report(self, analysis_results: Dict[str, Any]) -> str:
        """生成HTML报告"""
        logger.info("Generating HTML report...")
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>C Static Analysis Report</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
                .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .metrics { display: flex; flex-wrap: wrap; gap: 20px; }
                .metric-card { background: #f9f9f9; padding: 15px; border-radius: 5px; min-width: 200px; }
                .metric-value { font-size: 24px; font-weight: bold; color: #2196F3; }
                .metric-label { color: #666; }
                table { border-collapse: collapse; width: 100%; margin: 10px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .high-coupling { background-color: #ffebee; }
                .medium-coupling { background-color: #fff8e1; }
                .low-coupling { background-color: #e8f5e8; }
                .highlight { background-color: yellow; }
                .dependency { border-left: 3px solid blue; padding-left: 5px; }
                pre { background-color: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }
                .code-line { margin: 2px 0; padding: 2px 5px; }
                .code-line:hover { background-color: #e3f2fd; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>C语言静态分析报告</h1>
                <p>生成时间: {timestamp}</p>
                <p>分析文件: {source_file}</p>
            </div>
            
            <div class="section">
                <h2>分析概览</h2>
                <div class="metrics">
                    {overview_metrics}
                </div>
            </div>
            
            <div class="section">
                <h2>函数调用图统计</h2>
                {call_graph_stats}
            </div>
            
            <div class="section">
                <h2>耦合度分析</h2>
                {coupling_analysis}
            </div>
            
            <div class="section">
                <h2>数据流分析结果</h2>
                {dataflow_results}
            </div>
            
            <div class="section">
                <h2>程序依赖图统计</h2>
                {pdg_stats}
            </div>
            
            <div class="section">
                <h2>优化建议</h2>
                {optimization_suggestions}
            </div>
        </body>
        </html>
        """
        
        # 生成各个部分的内容
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        source_file = getattr(self.tu, 'spelling', 'Unknown')
        
        overview_metrics = self._generate_overview_metrics(analysis_results)
        call_graph_stats = self._generate_call_graph_stats(analysis_results)
        coupling_analysis = self._generate_coupling_analysis(analysis_results)
        dataflow_results = self._generate_dataflow_results(analysis_results)
        pdg_stats = self._generate_pdg_stats(analysis_results)
        optimization_suggestions = self._generate_optimization_suggestions(analysis_results)
        
        return html_template.format(
            timestamp=timestamp,
            source_file=source_file,
            overview_metrics=overview_metrics,
            call_graph_stats=call_graph_stats,
            coupling_analysis=coupling_analysis,
            dataflow_results=dataflow_results,
            pdg_stats=pdg_stats,
            optimization_suggestions=optimization_suggestions
        )
    
# 导出主要类
__all__ = ['AdvancedGraphVisualizer', 'SourceMapper', 'GraphVisualizer']