# -*- coding: utf-8 -*-
import sys
import os
import math
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QSpinBox, QPushButton)
from PyQt6.QtCore import QTimer, Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush

# 自动处理路径
current_dir = os.path.dirname(os.path.abspath(__file__))
possible_paths = [
    os.path.join(current_dir, "..", "build"),
    os.path.join(current_dir, "..", "build", "Release"),
]
for path in possible_paths:
    if os.path.exists(path):
        sys.path.append(path)

try:
    import sim_core
except ImportError:
    print("Fatal Error: Could not find sim_core.pyd. Please compile C++ code.")
    sys.exit(1)

class DiningWidget(QWidget):
    def __init__(self, simulation, n_p, n_f):
        super().__init__()
        self.sim = simulation
        self.n_p = n_p  # 哲学家人数
        self.n_f = n_f  # 叉子数量
        self.states = [0] * n_p
        self.edges = []
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(50)

    def update_data(self):
        try:
            self.states = self.sim.get_states()
            self.edges = self.sim.get_resource_graph()
            self.update()
        except Exception as e:
            print(f"Sync Error: {e}")

    def get_coords(self, index, is_philosopher=True):
        """核心修改：根据各自的总数计算角度"""
        width, height = self.width(), self.height()
        center_x, center_y = width / 2, height / 2
        
        if is_philosopher:
            radius = min(width, height) * 0.35
            # 哲学家均匀分布在圆周
            angle = (index * (2 * math.pi / self.n_p)) - math.pi / 2
        else:
            radius = min(width, height) * 0.22
            # 叉子均匀分布在内圈圆周
            angle = (index * (2 * math.pi / self.n_f)) - math.pi / 2
        
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        return QPointF(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. 绘制桌子
        painter.setBrush(QColor(245, 245, 245))
        painter.setPen(QPen(QColor(220, 220, 220), 2))
        painter.drawEllipse(QPointF(self.width()/2, self.height()/2), 
                           min(self.width(), self.height())*0.4, 
                           min(self.width(), self.height())*0.4)

        # 2. 绘制资源关系边 (RAG)
        for p_id, f_id, edge_type in self.edges:
            # 防护：确保索引不越界（在动态重置瞬间可能发生）
            if p_id >= self.n_p or f_id >= self.n_f: continue
            
            p_pos = self.get_coords(p_id, True)
            f_pos = self.get_coords(f_id, False)
            
            if edge_type == 0:  # Request (P->F)
                painter.setPen(QPen(QColor(255, 0, 0, 150), 2, Qt.PenStyle.DashLine))
                painter.drawLine(p_pos, f_pos)
            else:               # Allocation (F->P)
                painter.setPen(QPen(QColor(0, 180, 0, 200), 3))
                painter.drawLine(f_pos, p_pos)

        # 3. 绘制哲学家
        for i in range(self.n_p):
            pos = self.get_coords(i, True)
            color = [QColor("lightgray"), QColor(255, 120, 120), QColor(120, 255, 120)][self.states[i]]
            painter.setBrush(color)
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.drawEllipse(pos, 22, 22)
            painter.drawText(int(pos.x()-10), int(pos.y()+5), f"P{i}")

        # 4. 绘制叉子
        for i in range(self.n_f):
            pos = self.get_coords(i, False)
            painter.setBrush(QBrush(QColor("gold")))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawRect(int(pos.x()-5), int(pos.y()-5), 10, 10)
            painter.drawText(int(pos.x()-5), int(pos.y()-8), f"F{i}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Philosophers Lab: Dynamic Resource Configuration")
        self.resize(1000, 900)
        
        self.sim = None
        self.canvas = None
        self.init_ui()
        self.restart_simulation()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # 控制面板
        ctrl_layout = QHBoxLayout()
        
        self.p_input = QSpinBox()
        self.p_input.setRange(2, 15)
        self.p_input.setValue(5)
        
        self.f_input = QSpinBox()
        self.f_input.setRange(2, 15)
        self.f_input.setValue(4)
        
        btn = QPushButton("Apply & Reset Simulation")
        btn.clicked.connect(self.restart_simulation)
        btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;")

        ctrl_layout.addWidget(QLabel("Philosophers (N):"))
        ctrl_layout.addWidget(self.p_input)
        ctrl_layout.addWidget(QLabel("Forks (M):"))
        ctrl_layout.addWidget(self.f_input)
        ctrl_layout.addWidget(btn)
        
        main_layout.addLayout(ctrl_layout)
        
        # 绘图区域容器
        self.container = QWidget()
        self.canvas_layout = QVBoxLayout(self.container)
        main_layout.addWidget(self.container)
        
        # 状态说明
        info = QLabel("Logic: Banker's Algorithm enabled | Red Dash: P waits for F | Green Solid: P holds F")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(info)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def restart_simulation(self):
        # 1. 停止旧模拟
        if self.sim:
            self.sim.stop()
        
        # 2. 获取新参数
        np = self.p_input.value()
        nf = self.f_input.value()
        
        # 3. 创建新对象并启动
        self.sim = sim_core.Simulation(np, nf)
        self.sim.start()
        
        # 4. 刷新画布组件
        if self.canvas:
            self.canvas_layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            
        self.canvas = DiningWidget(self.sim, np, nf)
        self.canvas_layout.addWidget(self.canvas)

    def closeEvent(self, event):
        if self.sim: self.sim.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())