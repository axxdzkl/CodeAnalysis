#!/usr/bin/env python3
"""
Enhanced Project Dependency Visualizer

Generates comprehensive static visualizations for Redis project dependencies
including function dependency graphs, data dependency graphs, and module coupling graphs.
"""

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import FancyBboxPatch
import os
from pathlib import Path
import json

class ProjectDependencyVisualizer:
    """Enhanced visualizer for project-level dependency graphs"""
    
    def __init__(self, output_dir="project_dependency_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Set up matplotlib style
        plt.style.use('default')
        plt.rcParams['font.size'] = 10
        plt.rcParams['figure.facecolor'] = 'white'
    
    def visualize_function_dependencies(self, function_graph, title="Redis Function Dependencies"):
        """Generate function dependency visualization"""
        if function_graph.number_of_nodes() == 0:
            return None
            
        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        
        # Sample large graphs for visualization
        if function_graph.number_of_nodes() > 100:
            # Get most important nodes based on degree centrality
            centrality = nx.degree_centrality(function_graph)
            top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:100]
            sample_nodes = [node for node, _ in top_nodes]
            graph = function_graph.subgraph(sample_nodes)
        else:
            graph = function_graph
        
        # Use hierarchical layout for better structure
        try:
            pos = nx.spring_layout(graph, k=2, iterations=50, seed=42)
        except:
            pos = nx.random_layout(graph, seed=42)
        
        # Color nodes by file
        files = set([node.split('::')[0] for node in graph.nodes()])
        file_colors = plt.cm.Set3(np.linspace(0, 1, len(files)))
        color_map = {file: color for file, color in zip(files, file_colors)}
        
        node_colors = [color_map[node.split('::')[0]] for node in graph.nodes()]
        
        # Draw the graph
        nx.draw_networkx_nodes(graph, pos, node_color=node_colors, 
                              node_size=50, alpha=0.8, ax=ax)
        nx.draw_networkx_edges(graph, pos, edge_color='gray', 
                              alpha=0.6, width=0.5, arrows=True, 
                              arrowstyle='->', arrowsize=10, ax=ax)
        
        # Add labels for important nodes only
        important_nodes = dict(sorted(nx.degree_centrality(graph).items(), 
                                    key=lambda x: x[1], reverse=True)[:20])
        labels = {node: node.split('::')[1][:8] for node in important_nodes.keys()}
        nx.draw_networkx_labels(graph, pos, labels, font_size=8, ax=ax)
        
        ax.set_title(f"{title}\\n({graph.number_of_nodes()} functions, {graph.number_of_edges()} dependencies)", 
                    fontsize=14, fontweight='bold')
        ax.axis('off')
        
        # Add legend
        legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                     markerfacecolor=color_map[file], markersize=8, 
                                     label=file[:15]) for file in list(files)[:10]]
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
        
        plt.tight_layout()
        output_path = self.output_dir / "function_dependencies.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def visualize_module_coupling(self, module_graph, title="Redis Module Coupling"):
        """Generate module coupling visualization"""
        if module_graph.number_of_nodes() == 0:
            return None
            
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        
        # Use circular layout for modules
        pos = nx.circular_layout(module_graph)
        
        # Node sizes based on number of functions
        node_sizes = []
        for node in module_graph.nodes():
            functions = module_graph.nodes[node].get('functions', 1)
            node_sizes.append(min(functions * 20, 1000))  # Scale node size
        
        # Edge weights for coupling strength
        edges = module_graph.edges()
        edge_weights = [module_graph[u][v].get('weight', 1) for u, v in edges]
        max_weight = max(edge_weights) if edge_weights else 1
        edge_widths = [w / max_weight * 5 for w in edge_weights]
        
        # Color nodes by complexity
        node_colors = []
        for node in module_graph.nodes():
            complexity = module_graph.nodes[node].get('complexity', 1)
            node_colors.append(complexity)
        
        # Draw the graph
        nodes = nx.draw_networkx_nodes(module_graph, pos, 
                                     node_size=node_sizes,
                                     node_color=node_colors,
                                     cmap=plt.cm.Reds,
                                     alpha=0.8, ax=ax)
        
        nx.draw_networkx_edges(module_graph, pos,
                              width=edge_widths,
                              alpha=0.6,
                              edge_color='darkblue',
                              arrows=True,
                              arrowstyle='->',
                              arrowsize=20, ax=ax)
        
        # Add labels
        labels = {node: node.replace('.c', '') for node in module_graph.nodes()}
        nx.draw_networkx_labels(module_graph, pos, labels, 
                               font_size=9, font_weight='bold', ax=ax)
        
        ax.set_title(f"{title}\\n({module_graph.number_of_nodes()} modules, {module_graph.number_of_edges()} couplings)", 
                    fontsize=14, fontweight='bold')
        ax.axis('off')
        
        # Add colorbar for complexity
        if nodes:
            cbar = plt.colorbar(nodes, ax=ax, shrink=0.8)
            cbar.set_label('Module Complexity', rotation=270, labelpad=20)
        
        plt.tight_layout()
        output_path = self.output_dir / "module_coupling.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def visualize_data_dependencies(self, data_graph, title="Redis Data Dependencies"):
        """Generate data dependency visualization"""
        if data_graph.number_of_nodes() == 0:
            return None
            
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        # Use hierarchical layout
        pos = nx.spring_layout(data_graph, k=3, iterations=50)
        
        # Draw nodes
        nx.draw_networkx_nodes(data_graph, pos, 
                              node_color='lightblue',
                              node_size=800,
                              alpha=0.8, ax=ax)
        
        # Draw edges with different colors for different data types
        edge_colors = []
        for u, v, d in data_graph.edges(data=True):
            data_var = d.get('data_variable', 'unknown')
            if 'server' in data_var:
                edge_colors.append('red')
            elif 'client' in data_var:
                edge_colors.append('blue')
            elif 'dict' in data_var:
                edge_colors.append('green')
            else:
                edge_colors.append('gray')
        
        nx.draw_networkx_edges(data_graph, pos,
                              edge_color=edge_colors,
                              width=2,
                              alpha=0.7,
                              arrows=True,
                              arrowstyle='->',
                              arrowsize=20, ax=ax)
        
        # Add labels
        labels = {node: node.replace('.c', '') for node in data_graph.nodes()}
        nx.draw_networkx_labels(data_graph, pos, labels, 
                               font_size=10, font_weight='bold', ax=ax)
        
        ax.set_title(f"{title}\\n({data_graph.number_of_nodes()} modules, {data_graph.number_of_edges()} data dependencies)", 
                    fontsize=14, fontweight='bold')
        ax.axis('off')
        
        # Add legend for data types
        legend_elements = [
            plt.Line2D([0], [0], color='red', lw=2, label='Server Data'),
            plt.Line2D([0], [0], color='blue', lw=2, label='Client Data'),
            plt.Line2D([0], [0], color='green', lw=2, label='Dictionary Data'),
            plt.Line2D([0], [0], color='gray', lw=2, label='Other Data')
        ]
        ax.legend(handles=legend_elements, loc='upper left')
        
        plt.tight_layout()
        output_path = self.output_dir / "data_dependencies.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def create_summary_dashboard(self, stats, graphs_info):
        """Create a summary dashboard with all dependency information"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Statistics overview
        categories = ['Functions', 'Function Deps', 'Data Deps', 'Module Couplings', 'Circular Deps']
        values = [stats['total_functions'], stats['function_dependencies'], 
                 stats['data_dependencies'], stats['module_couplings'], 
                 stats['circular_dependencies']]
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        bars = ax1.bar(categories, values, color=colors, alpha=0.8)
        ax1.set_title('Redis Project Dependency Statistics', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Count')
        ax1.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.01,
                    f'{value}', ha='center', va='bottom', fontweight='bold')
        
        # Circular dependency warning
        ax2.text(0.5, 0.7, f"⚠️ Circular Dependencies", ha='center', va='center', 
                fontsize=16, fontweight='bold', color='red', transform=ax2.transAxes)
        ax2.text(0.5, 0.5, f"{stats['circular_dependencies']} detected", ha='center', va='center', 
                fontsize=20, fontweight='bold', transform=ax2.transAxes)
        ax2.text(0.5, 0.3, "May impact maintainability", ha='center', va='center', 
                fontsize=12, style='italic', transform=ax2.transAxes)
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2.axis('off')
        
        # Top coupling pairs
        if 'top_couplings' in graphs_info:
            couplings = graphs_info['top_couplings'][:5]
            coupling_labels = [f"{c[0]}\\n→\\n{c[1]}" for c in couplings]
            coupling_values = [c[2] for c in couplings]
            
            ax3.barh(range(len(coupling_labels)), coupling_values, color='orange', alpha=0.7)
            ax3.set_yticks(range(len(coupling_labels)))
            ax3.set_yticklabels(coupling_labels, fontsize=8)
            ax3.set_title('Top Module Couplings', fontsize=14, fontweight='bold')
            ax3.set_xlabel('Coupling Strength')
        else:
            ax3.text(0.5, 0.5, 'Module Coupling\\nAnalysis Complete', ha='center', va='center',
                    fontsize=14, fontweight='bold', transform=ax3.transAxes)
            ax3.axis('off')
        
        # Recommendations
        recommendations = [
            "• Review high coupling modules",
            "• Break circular dependencies", 
            "• Optimize data flow patterns",
            "• Consider module refactoring",
            "• Implement dependency injection"
        ]
        
        ax4.text(0.05, 0.95, "📈 Recommendations:", ha='left', va='top', 
                fontsize=14, fontweight='bold', transform=ax4.transAxes)
        
        for i, rec in enumerate(recommendations):
            ax4.text(0.05, 0.8 - i*0.15, rec, ha='left', va='top', 
                    fontsize=11, transform=ax4.transAxes)
        
        ax4.set_xlim(0, 1)
        ax4.set_ylim(0, 1)
        ax4.axis('off')
        
        plt.suptitle('Redis Project Dependency Analysis Dashboard', 
                    fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        output_path = self.output_dir / "dependency_dashboard.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)