#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRT 转 ASS 字幕转换器 - 标准PyQt5版本
实现与原版相同的功能和UI效果，但仅使用标准PyQt5组件
"""

import sys
import os
import json
import pysubs2
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem, QCheckBox, QLabel, QPushButton,
                             QDialog, QFormLayout, QLineEdit, QTimeEdit, QTextEdit, QDialogButtonBox,
                             QFileDialog, QColorDialog, QAbstractItemView, QSystemTrayIcon, QMenu, QMessageBox,
                             QFontDialog, QTabWidget, QFrame, QScrollArea, QSizePolicy, QSpacerItem, QStackedWidget,
                             QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject, QTime, QTimer
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPainter, QBrush, QPen

CONFIG_FILE = 'sub.json'
SETTINGS_FILE = 'settings.json'

class ModernCard(QFrame):
    """现代化卡片组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 5px;
            }
        """)

class ModernButton(QPushButton):
    """现代化按钮组件"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(28)  # 适中的按钮高度
        self.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                border: 1px solid #106EBE;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #106EBE;
                border: 1px solid #005A9E;
            }
            QPushButton:pressed {
                background-color: #005A9E;
                border: 1px solid #004578;
            }
            QPushButton:disabled {
                background-color: #404040;
                border: 1px solid #606060;
                color: #A0A0A0;
            }
        """)

class ModernLabel(QLabel):
    """现代化标签组件"""
    def __init__(self, text="", label_type="body", parent=None):
        super().__init__(text, parent)
        if label_type == "title":
            self.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 26px;
                    font-weight: bold;
                    margin: 12px 0;
                }
            """)
        elif label_type == "subtitle":
            self.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 18px;
                    font-weight: bold;
                    margin: 10px 0;
                }
            """)
        else:  # body
            self.setStyleSheet("""
                QLabel {
                    color: #E0E0E0;
                    font-size: 13px;
                    margin: 4px 0;
                }
            """)

class FloatingInfoBar(QFrame):
    """精美的浮动信息提示条"""
    def __init__(self, title, content, bar_type="info", parent=None):
        super().__init__(parent)

        # 根据内容长度动态计算高度
        content_lines = len(content) // 40 + 1  # 估算行数（每行约40字符）
        if '\n' in content:
            content_lines = max(content_lines, content.count('\n') + 1)

        # 设置合理的高度范围
        min_height = 70
        max_height = 120
        calculated_height = min_height + (content_lines - 1) * 20
        final_height = max(min_height, min(calculated_height, max_height))

        self.setFixedSize(380, final_height)  # 增大宽度，动态高度
        self.setFrameStyle(QFrame.NoFrame)

        # 设置为浮动窗口
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 根据类型设置渐变颜色和图标
        if bar_type == "success":
            self.bg_gradient = """qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(34, 197, 94, 0.95),
                stop:0.5 rgba(16, 185, 129, 0.95),
                stop:1 rgba(5, 150, 105, 0.95))"""
            self.border_color = "#22C55E"
            self.icon_color = "#FFFFFF"
            self.shadow_color = "rgba(34, 197, 94, 0.4)"
        elif bar_type == "warning":
            self.bg_gradient = """qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(251, 191, 36, 0.95),
                stop:0.5 rgba(245, 158, 11, 0.95),
                stop:1 rgba(217, 119, 6, 0.95))"""
            self.border_color = "#F59E0B"
            self.icon_color = "#FFFFFF"
            self.shadow_color = "rgba(251, 191, 36, 0.4)"
        elif bar_type == "error":
            self.bg_gradient = """qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(239, 68, 68, 0.95),
                stop:0.5 rgba(220, 38, 38, 0.95),
                stop:1 rgba(185, 28, 28, 0.95))"""
            self.border_color = "#EF4444"
            self.icon_color = "#FFFFFF"
            self.shadow_color = "rgba(239, 68, 68, 0.4)"
        else:  # info
            self.bg_gradient = """qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(59, 130, 246, 0.95),
                stop:0.5 rgba(37, 99, 235, 0.95),
                stop:1 rgba(29, 78, 216, 0.95))"""
            self.border_color = "#3B82F6"
            self.icon_color = "#FFFFFF"
            self.shadow_color = "rgba(59, 130, 246, 0.4)"

        # 创建阴影效果的外层容器
        shadow_width = self.width() - 4
        shadow_height = self.height() - 4
        self.shadow_frame = QFrame(self)
        self.shadow_frame.setGeometry(4, 4, shadow_width, shadow_height)
        self.shadow_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.shadow_color};
                border-radius: 12px;
            }}
        """)

        # 主内容框架
        content_width = self.width()
        content_height = self.height()
        self.content_frame = QFrame(self)
        self.content_frame.setGeometry(0, 0, content_width, content_height)
        self.content_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.bg_gradient};
                border: 2px solid {self.border_color};
                border-radius: 12px;
            }}
            QLabel {{
                color: #FFFFFF;
                border: none;
                font-weight: bold;
            }}
        """)

        # 在主内容框架上创建布局
        layout = QHBoxLayout(self.content_frame)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(12)

        # 图标区域（使用更精美的图标）
        icon_map = {
            "success": "✓",
            "warning": "⚠",
            "error": "✕",
            "info": "ⓘ"
        }

        # 创建图标容器
        icon_container = QFrame()
        icon_container.setFixedSize(32, 32)
        icon_container.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 16px;
            }}
        """)

        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(icon_map.get(bar_type, "ⓘ"))
        icon_label.setFont(QFont("", 16, QFont.Bold))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"color: {self.icon_color};")
        icon_layout.addWidget(icon_label)

        layout.addWidget(icon_container)

        # 文字区域
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        title_label = QLabel(title)
        title_label.setFont(QFont("", 12, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
        """)
        text_layout.addWidget(title_label)

        content_label = QLabel(content)
        content_label.setFont(QFont("", 10))
        content_label.setWordWrap(True)
        content_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 顶部对齐
        content_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-weight: 400;
                line-height: 1.4;
            }
        """)
        text_layout.addWidget(content_label)
        text_layout.addStretch()  # 添加弹性空间，确保内容顶部对齐

        layout.addWidget(text_widget)

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.4);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.15);
            }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        # 自动消失定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.fade_out)
        self.timer.start(4000)  # 延长显示时间

        # 淡入效果
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)

        # 添加进入动画
        self.slide_in()

    def slide_in(self):
        """滑入动画"""
        self.opacity_effect.setOpacity(0.0)

        # 获取最终位置
        final_pos = self.pos()

        # 从右侧滑入
        start_x = final_pos.x() + 100
        self.move(start_x, final_pos.y())
        self.show()

        # 动画参数
        self.animation_timer = QTimer()
        self.animation_step = 0
        self.total_steps = 20
        self.start_x = start_x
        self.final_x = final_pos.x()

        def update_animation():
            self.animation_step += 1
            progress = self.animation_step / self.total_steps

            # 使用缓动函数
            eased_progress = 1 - (1 - progress) ** 3  # ease-out cubic

            # 更新位置
            current_x = self.start_x + (self.final_x - self.start_x) * eased_progress
            self.move(int(current_x), final_pos.y())

            # 更新透明度
            self.opacity_effect.setOpacity(eased_progress)

            if self.animation_step >= self.total_steps:
                self.animation_timer.stop()
                self.move(self.final_x, final_pos.y())
                self.opacity_effect.setOpacity(1.0)

        self.animation_timer.timeout.connect(update_animation)
        self.animation_timer.start(30)  # 30ms间隔，更流畅

    def fade_out(self):
        """滑出动画"""
        # 停止自动消失定时器
        if hasattr(self, 'timer'):
            self.timer.stop()

        # 获取当前位置
        current_pos = self.pos()

        # 动画参数
        self.fade_timer = QTimer()
        self.fade_step = 0
        self.fade_steps = 15
        self.start_x = current_pos.x()
        self.end_x = current_pos.x() + 100

        def update_fade():
            self.fade_step += 1
            progress = self.fade_step / self.fade_steps

            # 使用缓动函数
            eased_progress = progress ** 2  # ease-in

            # 更新位置
            current_x = self.start_x + (self.end_x - self.start_x) * eased_progress
            self.move(int(current_x), current_pos.y())

            # 更新透明度
            opacity = 1.0 - eased_progress
            self.opacity_effect.setOpacity(opacity)

            if self.fade_step >= self.fade_steps:
                self.fade_timer.stop()
                self.close()

        self.fade_timer.timeout.connect(update_fade)
        self.fade_timer.start(40)  # 稍快的退出动画

class DragDropListWidget(QListWidget):
    """支持拖拽的文件列表组件"""
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(200)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #808080;
                border-radius: 8px;
                background-color: #3A3A3A;
                padding: 12px;
                font-size: 13px;
                color: #FFFFFF;
            }
            QListWidget::item {
                padding: 10px;
                margin: 3px;
                border-radius: 5px;
                background-color: #4A4A4A;
                color: #FFFFFF;
                border: 1px solid #606060;
            }
            QListWidget::item:selected {
                background-color: #0078D4;
                border: 1px solid #106EBE;
            }
            QListWidget::item:hover {
                background-color: #505050;
                border: 1px solid #707070;
            }
        """)

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            valid_files = []
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.srt', '.vtt', '.ass')):
                    valid_files.append(file_path)

            if valid_files:
                event.acceptProposedAction()
                self.setStyleSheet("""
                    QListWidget {
                        border: 2px solid #00D4FF;
                        border-radius: 8px;
                        background-color: #2A4A5A;
                        padding: 12px;
                        font-size: 13px;
                        color: #FFFFFF;
                    }
                    QListWidget::item {
                        padding: 10px;
                        margin: 3px;
                        border-radius: 5px;
                        background-color: #4A6A7A;
                        color: #FFFFFF;
                        border: 1px solid #00D4FF;
                    }
                    QListWidget::item:selected {
                        background-color: #0078D4;
                        border: 1px solid #106EBE;
                    }
                    QListWidget::item:hover {
                        background-color: #5A7A8A;
                        border: 1px solid #00E4FF;
                    }
                """)
            else:
                event.ignore()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            valid_files = []
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.srt', '.vtt', '.ass')):
                    valid_files.append(file_path)

            if valid_files:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #808080;
                border-radius: 8px;
                background-color: #3A3A3A;
                padding: 12px;
                font-size: 13px;
                color: #FFFFFF;
            }
            QListWidget::item {
                padding: 10px;
                margin: 3px;
                border-radius: 5px;
                background-color: #4A4A4A;
                color: #FFFFFF;
                border: 1px solid #606060;
            }
            QListWidget::item:selected {
                background-color: #0078D4;
                border: 1px solid #106EBE;
            }
            QListWidget::item:hover {
                background-color: #505050;
                border: 1px solid #707070;
            }
        """)
        event.accept()

    def dropEvent(self, event):
        """拖拽放下事件"""
        if event.mimeData().hasUrls():
            files = []
            urls = event.mimeData().urls()

            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.srt', '.vtt', '.ass')):
                    files.append(file_path)

            if files:
                self.files_dropped.emit(files)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

        self.dragLeaveEvent(event)

class CheckableListWidget(QListWidget):
    """可选择的列表组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setStyleSheet("""
            QListWidget {
                background-color: #3A3A3A;
                border: 1px solid #606060;
                border-radius: 6px;
                padding: 8px;
                color: #FFFFFF;
            }
            QListWidget::item {
                padding: 6px;
                margin: 2px;
                border-radius: 3px;
                background-color: #4A4A4A;
            }
        """)

    def addCheckableItem(self, text, checked=False):
        item = QListWidgetItem(self)
        self.addItem(item)
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        checkbox.setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgba(120, 120, 120, 0.7);
                border-radius: 5px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(65, 65, 65, 0.95),
                    stop:1 rgba(50, 50, 50, 0.95));
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4A9EFF,
                    stop:0.5 #0078D4,
                    stop:1 #005A9E);
                border: 2px solid #4A9EFF;
                border-top: 2px solid #6AB8FF;
            }
            QCheckBox::indicator:hover {
                border: 2px solid rgba(74, 158, 255, 0.8);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(85, 85, 85, 0.95),
                    stop:1 rgba(70, 70, 70, 0.95));
            }
            QCheckBox::indicator:checked:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5AAFFF,
                    stop:0.5 #1088E4,
                    stop:1 #0066B4);
                border: 2px solid #5AAFFF;
            }
        """)
        self.setItemWidget(item, checkbox)

    def getCheckedItems(self):
        return [
            self.itemWidget(self.item(i)).text()
            for i in range(self.count())
            if isinstance(self.itemWidget(self.item(i)), QCheckBox) and
               self.itemWidget(self.item(i)).isChecked()
        ]

class CustomSideTabWidget(QWidget):
    """自定义左侧标签页组件，确保文字水平显示"""
    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_index = 0
        self.tabs = []
        self.tab_buttons = []
        self.setupUI()

    def setupUI(self):
        # 主布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧按钮区域
        self.button_widget = QWidget()
        self.button_widget.setFixedWidth(150)
        self.button_widget.setStyleSheet("""
            QWidget {
                background-color: #3A3A3A;
                border-right: 2px solid #606060;
            }
        """)

        self.button_layout = QVBoxLayout(self.button_widget)
        self.button_layout.setContentsMargins(10, 16, 10, 16)  # 精细化边距
        self.button_layout.setSpacing(8)   # 适中的间距

        # 右侧内容区域
        self.content_widget = QStackedWidget()
        self.content_widget.setStyleSheet("""
            QStackedWidget {
                background-color: #2B2B2B;
                border: none;
            }
        """)

        main_layout.addWidget(self.button_widget)
        main_layout.addWidget(self.content_widget)

        # 添加弹性空间到按钮布局底部
        self.button_layout.addStretch()

    def addTab(self, widget, text):
        # 创建标签按钮
        button = QPushButton(text)
        button.setCheckable(True)
        button.setMinimumHeight(36)  # 适中的导航按钮高度
        button.setStyleSheet("""
            QPushButton {
                background-color: #4A4A4A;
                border: 2px solid #606060;
                border-radius: 8px;
                color: #E0E0E0;
                font-size: 13px;
                font-weight: 600;
                text-align: center;
                padding: 10px 12px;
            }
            QPushButton:checked {
                background-color: #0078D4;
                border: 2px solid #106EBE;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
                border: 2px solid #707070;
                color: #FFFFFF;
            }
            QPushButton:checked:hover {
                background-color: #106EBE;
                border: 2px solid #005A9E;
            }
        """)

        # 连接按钮点击事件
        index = len(self.tabs)
        button.clicked.connect(lambda: self.setCurrentIndex(index))

        # 添加到布局（在弹性空间之前）
        self.button_layout.insertWidget(len(self.tab_buttons), button)

        # 添加到内容区域
        self.content_widget.addWidget(widget)

        # 保存引用
        self.tabs.append(widget)
        self.tab_buttons.append(button)

        # 如果是第一个标签，设为选中
        if index == 0:
            button.setChecked(True)
            self.content_widget.setCurrentWidget(widget)

    def setCurrentIndex(self, index):
        if 0 <= index < len(self.tabs):
            # 更新按钮状态
            for i, button in enumerate(self.tab_buttons):
                button.setChecked(i == index)

            # 切换内容
            self.content_widget.setCurrentWidget(self.tabs[index])

            # 发射信号
            if self.current_index != index:
                self.current_index = index
                self.currentChanged.emit(index)

    def currentIndex(self):
        return self.current_index
        return [
            self.itemWidget(self.item(i)).text()
            for i in range(self.count())
            if isinstance(self.itemWidget(self.item(i)), QCheckBox) and
               self.itemWidget(self.item(i)).isChecked()
        ]

class MainInterface(QScrollArea):
    """主界面 - 文件转换"""
    convert_requested = pyqtSignal(list, list, str, str, bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.subtitle_configs = []
        self.subtitle_color = 'H00FFFFFF'
        self.outline_color = 'H00000000'
        self.delete_original_after_convert = False
        self.convert_to_china = False
        self.output_directory = ""
        self.info_bars = []  # 存储信息提示条

        self.setupUI()

    def setupUI(self):
        """设置主界面UI"""
        self.setWidgetResizable(True)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #2b2b2b;
                border: none;
            }
        """)

        # 主容器 - 精细化间距和边距
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(14)  # 适中的组件间距
        main_layout.setContentsMargins(18, 18, 18, 18)  # 适中的容器边距

        # 浮动信息提示不需要布局容器
        self.info_bars = []  # 存储浮动信息条

        # 标题 - 减小字体和边距
        title = ModernLabel("字幕格式转换器", "title")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 22px;
                font-weight: bold;
                margin: 8px 0;
            }
        """)
        main_layout.addWidget(title)

        # 文件区域卡片 - 精细化内边距
        file_card = ModernCard()
        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(16, 14, 16, 14)  # 精细化内边距
        file_layout.setSpacing(10)  # 适中的组件间距

        file_title = ModernLabel("文件列表", "subtitle")
        file_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                margin: 4px 0;
            }
        """)
        file_layout.addWidget(file_title)

        # 文件列表 - 优化高度
        self.file_list = DragDropListWidget()
        self.file_list.setMinimumHeight(100)  # 紧凑的最小高度
        self.file_list.setMaximumHeight(160)  # 合理的最大高度限制
        self.file_list.files_dropped.connect(self.handle_dropped_files)

        # 添加占位符文本
        if self.file_list.count() == 0:
            placeholder_item = QListWidgetItem("拖拽 SRT、VTT 或 ASS 文件到此处，或点击'添加文件'按钮")
            placeholder_item.setFlags(Qt.NoItemFlags)
            placeholder_item.setTextAlignment(Qt.AlignCenter)
            self.file_list.addItem(placeholder_item)

        file_layout.addWidget(self.file_list)

        # 文件操作按钮 - 优化间距
        file_buttons_layout = QHBoxLayout()
        file_buttons_layout.setSpacing(10)  # 适中的按钮间距
        file_buttons_layout.setContentsMargins(0, 8, 0, 0)  # 顶部留出间距

        add_files_btn = ModernButton("添加文件")
        add_files_btn.clicked.connect(self.add_files)
        file_buttons_layout.addWidget(add_files_btn)

        remove_files_btn = ModernButton("删除选中")
        remove_files_btn.clicked.connect(self.remove_selected_files)
        file_buttons_layout.addWidget(remove_files_btn)

        clear_files_btn = ModernButton("清除全部")
        clear_files_btn.clicked.connect(self.clear_all_files)
        file_buttons_layout.addWidget(clear_files_btn)

        file_buttons_layout.addStretch()
        file_layout.addLayout(file_buttons_layout)

        main_layout.addWidget(file_card)

        # 配置区域 - 精细化布局
        config_layout = QHBoxLayout()
        config_layout.setSpacing(12)  # 适中的间距
        config_layout.setContentsMargins(0, 4, 0, 0)  # 顶部留出小间距

        # 字幕配置卡片 - 精细化内边距
        subtitle_card = ModernCard()
        subtitle_layout = QVBoxLayout(subtitle_card)
        subtitle_layout.setContentsMargins(14, 12, 14, 12)  # 精细化内边距
        subtitle_layout.setSpacing(8)   # 适中的间距

        subtitle_title = ModernLabel("字幕配置", "subtitle")
        subtitle_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                margin: 4px 0;
            }
        """)
        subtitle_layout.addWidget(subtitle_title)

        self.insert_options = CheckableListWidget()
        self.insert_options.setMaximumHeight(110)  # 进一步优化高度
        subtitle_layout.addWidget(self.insert_options)

        # 字幕配置按钮
        subtitle_buttons_layout = QHBoxLayout()

        add_config_btn = ModernButton("添加")
        add_config_btn.clicked.connect(self.add_subtitle_config)
        subtitle_buttons_layout.addWidget(add_config_btn)

        edit_config_btn = ModernButton("编辑")
        edit_config_btn.clicked.connect(self.edit_subtitle_config)
        subtitle_buttons_layout.addWidget(edit_config_btn)

        delete_config_btn = ModernButton("删除")
        delete_config_btn.clicked.connect(self.delete_subtitle_config)
        subtitle_buttons_layout.addWidget(delete_config_btn)

        subtitle_layout.addLayout(subtitle_buttons_layout)
        config_layout.addWidget(subtitle_card)

        # 选项卡片 - 精细化内边距
        options_card = ModernCard()
        options_layout = QVBoxLayout(options_card)
        options_layout.setContentsMargins(14, 12, 14, 12)  # 精细化内边距
        options_layout.setSpacing(8)   # 适中的间距

        options_title = ModernLabel("转换选项", "subtitle")
        options_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                margin: 4px 0;
            }
        """)
        options_layout.addWidget(options_title)

        # 删除原文件选项
        self.delete_original_checkbox = QCheckBox('转换后删除原文件')
        self.delete_original_checkbox.setChecked(True)
        self.delete_original_checkbox.setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgba(120, 120, 120, 0.7);
                border-radius: 5px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(65, 65, 65, 0.95),
                    stop:1 rgba(50, 50, 50, 0.95));
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4A9EFF,
                    stop:0.5 #0078D4,
                    stop:1 #005A9E);
                border: 2px solid #4A9EFF;
                border-top: 2px solid #6AB8FF;
            }
            QCheckBox::indicator:hover {
                border: 2px solid rgba(74, 158, 255, 0.8);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(85, 85, 85, 0.95),
                    stop:1 rgba(70, 70, 70, 0.95));
            }
            QCheckBox::indicator:checked:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5AAFFF,
                    stop:0.5 #1088E4,
                    stop:1 #0066B4);
                border: 2px solid #5AAFFF;
            }
        """)
        self.delete_original_checkbox.stateChanged.connect(self.on_delete_original_changed)
        options_layout.addWidget(self.delete_original_checkbox)

        # 繁体中国化选项
        self.convert_to_china_checkbox = QCheckBox('繁体中国化')
        self.convert_to_china_checkbox.setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgba(120, 120, 120, 0.7);
                border-radius: 5px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(65, 65, 65, 0.95),
                    stop:1 rgba(50, 50, 50, 0.95));
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4A9EFF,
                    stop:0.5 #0078D4,
                    stop:1 #005A9E);
                border: 2px solid #4A9EFF;
                border-top: 2px solid #6AB8FF;
            }
            QCheckBox::indicator:hover {
                border: 2px solid rgba(74, 158, 255, 0.8);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(85, 85, 85, 0.95),
                    stop:1 rgba(70, 70, 70, 0.95));
            }
            QCheckBox::indicator:checked:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5AAFFF,
                    stop:0.5 #1088E4,
                    stop:1 #0066B4);
                border: 2px solid #5AAFFF;
            }
        """)
        self.convert_to_china_checkbox.stateChanged.connect(self.on_convert_to_china_changed)
        options_layout.addWidget(self.convert_to_china_checkbox)

        # API优先选项
        self.api_priority_checkbox = QCheckBox('API优先转换')
        self.api_priority_checkbox.setChecked(True)  # 默认选中API优先
        self.api_priority_checkbox.setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgba(120, 120, 120, 0.7);
                border-radius: 5px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(65, 65, 65, 0.95),
                    stop:1 rgba(50, 50, 50, 0.95));
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4A9EFF,
                    stop:0.5 #0078D4,
                    stop:1 #005A9E);
                border: 2px solid #4A9EFF;
                border-top: 2px solid #6AB8FF;
            }
            QCheckBox::indicator:hover {
                border: 2px solid rgba(74, 158, 255, 0.8);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(85, 85, 85, 0.95),
                    stop:1 rgba(70, 70, 70, 0.95));
            }
            QCheckBox::indicator:checked:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5AAFFF,
                    stop:0.5 #1088E4,
                    stop:1 #0066B4);
                border: 2px solid #5AAFFF;
            }
        """)
        self.api_priority_checkbox.stateChanged.connect(self.on_api_priority_changed)
        options_layout.addWidget(self.api_priority_checkbox)

        options_layout.addStretch()
        config_layout.addWidget(options_card)

        main_layout.addLayout(config_layout)

        # 转换按钮 - 优化尺寸和布局
        convert_layout = QHBoxLayout()
        convert_layout.setContentsMargins(0, 12, 0, 8)  # 上下留出间距
        convert_layout.addStretch()

        self.convert_button = ModernButton("开始转换")
        self.convert_button.clicked.connect(self.start_convert)
        self.convert_button.setMinimumSize(110, 34)  # 精细化按钮尺寸
        self.convert_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                border: 2px solid #106EBE;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 15px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #106EBE;
                border: 2px solid #005A9E;
            }
            QPushButton:pressed {
                background-color: #005A9E;
                border: 2px solid #004578;
            }
            QPushButton:disabled {
                background-color: #404040;
                border: 2px solid #606060;
                color: #A0A0A0;
            }
        """)
        convert_layout.addWidget(self.convert_button)

        main_layout.addLayout(convert_layout)
        main_layout.addStretch()

        self.setWidget(main_widget)

    def show_info_bar(self, title, content, bar_type="info"):
        """显示浮动信息提示条"""
        # 清除旧的信息条
        for info_bar in self.info_bars:
            info_bar.close()
        self.info_bars.clear()

        # 创建新的浮动信息条
        info_bar = FloatingInfoBar(title, content, bar_type)
        self.info_bars.append(info_bar)

        # 计算显示位置（顶部垂直居中）
        try:
            # 获取主窗口的全局位置和尺寸
            main_window = self.parent
            if hasattr(main_window, 'geometry'):
                parent_rect = main_window.geometry()

                # 计算水平位置：窗口右侧，留出边距
                x = parent_rect.x() + parent_rect.width() - info_bar.width() - 30

                # 计算垂直位置：顶部区域垂直居中
                # 顶部区域定义为窗口上方1/4区域
                top_area_height = parent_rect.height() // 4
                title_bar_height = 35  # 考虑窗口标题栏
                y = parent_rect.y() + title_bar_height + (top_area_height - info_bar.height()) // 2

                # 确保不会超出屏幕边界
                from PyQt5.QtWidgets import QApplication
                screen = QApplication.desktop().screenGeometry()
                x = max(10, min(x, screen.width() - info_bar.width() - 10))
                y = max(10, min(y, screen.height() - info_bar.height() - 10))

                info_bar.move(x, y)
            else:
                # 备用方案：使用屏幕顶部居中
                from PyQt5.QtWidgets import QApplication
                screen = QApplication.desktop().screenGeometry()
                x = screen.width() - info_bar.width() - 30
                y = 80  # 固定在顶部
                info_bar.move(x, y)
        except Exception as e:
            # 最终备用方案
            info_bar.move(100, 100)

    def handle_dropped_files(self, files):
        """处理拖拽的文件"""
        if files:
            # 如果有占位符，先清除
            if self.file_list.count() == 1:
                first_item = self.file_list.item(0)
                if first_item and first_item.flags() == Qt.NoItemFlags:
                    self.file_list.clear()

            # 添加文件，避免重复
            existing_files = [self.file_list.item(i).text()
                            for i in range(self.file_list.count())]

            added_count = 0
            for file in files:
                if file not in existing_files:
                    self.file_list.addItem(file)
                    added_count += 1

            # 显示成功信息
            if added_count > 0:
                self.show_info_bar("文件添加成功", f"已添加 {added_count} 个文件", "success")

    def add_files(self):
        """添加文件"""
        try:
            home_dir = os.path.expanduser("~")
            files, _ = QFileDialog.getOpenFileNames(
                self,
                '选择SRT、VTT或ASS文件',
                home_dir,
                'Subtitle Files (*.srt *.vtt *.ass);;SRT Files (*.srt);;VTT Files (*.vtt);;ASS Files (*.ass);;All Files (*)'
            )

            if not files:
                return

            # 如果有占位符，先清除
            if self.file_list.count() == 1:
                first_item = self.file_list.item(0)
                if first_item and first_item.flags() == Qt.NoItemFlags:
                    self.file_list.clear()

            # 添加选择的文件
            for file in files:
                existing_files = [self.file_list.item(i).text()
                                for i in range(self.file_list.count())]
                if file not in existing_files:
                    self.file_list.addItem(file)

            # 显示成功信息
            if files:
                self.show_info_bar("文件添加成功", f"已添加 {len(files)} 个文件", "success")

        except Exception as e:
            self.show_info_bar("添加文件失败", f"错误: {str(e)}", "error")

    def remove_selected_files(self):
        """删除选中文件"""
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def clear_all_files(self):
        """清除所有文件"""
        self.file_list.clear()
        # 重新添加占位符
        placeholder_item = QListWidgetItem("拖拽 SRT、VTT 或 ASS 文件到此处，或点击'添加文件'按钮")
        placeholder_item.setFlags(Qt.NoItemFlags)
        placeholder_item.setTextAlignment(Qt.AlignCenter)
        self.file_list.addItem(placeholder_item)



    def on_delete_original_changed(self, state):
        """删除原文件选项改变"""
        self.delete_original_after_convert = state == Qt.Checked

    def on_convert_to_china_changed(self, state):
        """繁体中国化选项改变"""
        self.convert_to_china = state == Qt.Checked

    def on_api_priority_changed(self, state):
        """API优先选项改变"""
        self.api_priority = state == Qt.Checked

    def start_convert(self):
        """开始转换"""
        # 获取有效的文件列表（排除占位符）
        files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item and item.flags() != Qt.NoItemFlags:
                files.append(item.text())

        if len(files) == 0:
            self.show_info_bar("警告", "请先添加要转换的文件", "warning")
            return

        insert_options = self.insert_options.getCheckedItems()

        self.convert_requested.emit(
            files, insert_options, self.subtitle_color, self.outline_color,
            self.delete_original_after_convert, self.convert_to_china
        )

    def add_subtitle_config(self):
        """添加字幕配置"""
        dialog = SubtitleConfigDialog(parent=self)
        if dialog.exec_():
            config = dialog.get_config()
            self.subtitle_configs.append(config)
            self.parent.subtitle_configs.append(config)
            self.insert_options.addCheckableItem(config['name'])
            self.parent.save_subtitle_configs()

    def edit_subtitle_config(self):
        """编辑字幕配置"""
        checked_items = self.insert_options.getCheckedItems()
        if len(checked_items) != 1 or checked_items[0] == '不插入字幕':
            self.show_info_bar("提示", "请选择一个配置项进行编辑", "warning")
            return

        config_name = checked_items[0]
        config = next((c for c in self.subtitle_configs if c['name'] == config_name), None)
        if config:
            dialog = SubtitleConfigDialog(config, self)
            if dialog.exec_():
                new_config = dialog.get_config()
                index = next(i for i, c in enumerate(self.subtitle_configs) if c['name'] == config_name)
                self.subtitle_configs[index] = new_config
                parent_index = next(i for i, c in enumerate(self.parent.subtitle_configs) if c['name'] == config_name)
                self.parent.subtitle_configs[parent_index] = new_config
                self.parent.save_subtitle_configs()
                self.refresh_config_list()

    def delete_subtitle_config(self):
        """删除字幕配置"""
        checked_items = self.insert_options.getCheckedItems()
        if len(checked_items) != 1 or checked_items[0] == '不插入字幕':
            self.show_info_bar("提示", "请选择一个配置项进行删除", "warning")
            return

        config_name = checked_items[0]
        self.subtitle_configs = [c for c in self.subtitle_configs if c['name'] != config_name]
        self.parent.subtitle_configs = [c for c in self.parent.subtitle_configs if c['name'] != config_name]
        self.parent.save_subtitle_configs()
        self.refresh_config_list()

    def refresh_config_list(self):
        """刷新配置列表"""
        self.insert_options.clear()
        for config in self.subtitle_configs:
            self.insert_options.addCheckableItem(config['name'])
        self.insert_options.addCheckableItem('不插入字幕')

class SettingsInterface(QScrollArea):
    """设置界面"""
    config_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setupUI()

    def setupUI(self):
        """设置界面UI"""
        self.setWidgetResizable(True)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #2b2b2b;
                border: none;
            }
        """)

        # 主容器 - 精细化间距和边距
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(14)  # 适中的间距
        main_layout.setContentsMargins(18, 18, 18, 18)  # 适中的边距

        # 标题 - 减小字体
        title = ModernLabel("设置", "title")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: bold;
                margin: 6px 0;
            }
        """)
        main_layout.addWidget(title)

        # 输出目录设置卡片 - 精细化内边距
        output_card = ModernCard()
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(16, 14, 16, 14)  # 精细化内边距
        output_layout.setSpacing(8)   # 适中的间距

        output_title = ModernLabel("输出目录设置", "subtitle")
        output_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                margin: 4px 0;
            }
        """)
        output_layout.addWidget(output_title)

        # 输出目录选择
        output_dir_layout = QHBoxLayout()
        output_dir_label = ModernLabel("输出目录:")
        output_dir_layout.addWidget(output_dir_label)

        self.output_dir_display = ModernLabel("未设置（使用原文件目录）")
        self.output_dir_display.setStyleSheet("color: #B0B0B0; font-style: italic; font-weight: normal; font-size: 13px;")
        output_dir_layout.addWidget(self.output_dir_display)
        output_dir_layout.addStretch()

        self.choose_output_dir_btn = ModernButton("选择目录")
        self.choose_output_dir_btn.clicked.connect(self.choose_output_directory)
        output_dir_layout.addWidget(self.choose_output_dir_btn)

        self.clear_output_dir_btn = ModernButton("清除设置")
        self.clear_output_dir_btn.clicked.connect(self.clear_output_directory)
        output_dir_layout.addWidget(self.clear_output_dir_btn)

        output_layout.addLayout(output_dir_layout)

        # 输出目录说明
        output_info = ModernLabel("• 未设置时：文件保存在原文件相同目录\n• 已设置时：所有文件统一保存到指定目录")
        output_info.setStyleSheet("color: #A0A0A0; font-size: 12px;")
        output_layout.addWidget(output_info)

        main_layout.addWidget(output_card)

        # 颜色设置卡片 - 减少内边距
        color_card = ModernCard()
        color_layout = QVBoxLayout(color_card)
        color_layout.setContentsMargins(12, 12, 12, 12)  # 从20减少到12
        color_layout.setSpacing(6)  # 减少间距

        color_title = ModernLabel("字幕颜色设置", "subtitle")
        color_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                margin: 4px 0;
            }
        """)
        color_layout.addWidget(color_title)

        # 字幕颜色
        subtitle_color_layout = QHBoxLayout()
        subtitle_color_label = ModernLabel("字幕颜色:")
        subtitle_color_layout.addWidget(subtitle_color_label)

        self.subtitle_color_button = ModernButton("选择颜色")
        self.subtitle_color_button.clicked.connect(lambda: self.choose_color('subtitle'))
        subtitle_color_layout.addWidget(self.subtitle_color_button)
        subtitle_color_layout.addStretch()

        color_layout.addLayout(subtitle_color_layout)

        # 边框颜色
        outline_color_layout = QHBoxLayout()
        outline_color_label = ModernLabel("边框颜色:")
        outline_color_layout.addWidget(outline_color_label)

        self.outline_color_button = ModernButton("选择颜色")
        self.outline_color_button.clicked.connect(lambda: self.choose_color('outline'))
        outline_color_layout.addWidget(self.outline_color_button)
        outline_color_layout.addStretch()

        color_layout.addLayout(outline_color_layout)
        main_layout.addWidget(color_card)

        # 字体设置卡片 - 减少内边距
        font_card = ModernCard()
        font_layout = QVBoxLayout(font_card)
        font_layout.setContentsMargins(12, 12, 12, 12)  # 从20减少到12
        font_layout.setSpacing(6)  # 减少间距

        font_title = ModernLabel("字体设置", "subtitle")
        font_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                margin: 4px 0;
            }
        """)
        font_layout.addWidget(font_title)

        # 字体选择
        font_selection_layout = QHBoxLayout()
        font_label = ModernLabel("字幕字体:")
        font_selection_layout.addWidget(font_label)

        self.font_display = ModernLabel("方正粗圆_GBK, 70pt")
        self.font_display.setStyleSheet("color: #B0B0B0; font-style: italic; font-weight: normal; font-size: 13px;")
        font_selection_layout.addWidget(self.font_display)
        font_selection_layout.addStretch()

        self.choose_font_btn = ModernButton("选择字体")
        self.choose_font_btn.clicked.connect(self.choose_font)
        font_selection_layout.addWidget(self.choose_font_btn)

        self.reset_font_btn = ModernButton("重置默认")
        self.reset_font_btn.clicked.connect(self.reset_font)
        font_selection_layout.addWidget(self.reset_font_btn)

        font_layout.addLayout(font_selection_layout)

        # 字体预览
        self.font_preview = ModernLabel("字幕预览效果 Subtitle Preview 字幕样式测试")
        self.font_preview.setStyleSheet("""
            QLabel {
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 10px;
                background-color: rgba(0, 0, 0, 0.8);
                color: white;
                font-size: 16px;
            }
        """)
        self.font_preview.setAlignment(Qt.AlignCenter)
        font_layout.addWidget(self.font_preview)

        # 字体说明
        font_info = ModernLabel("• 字体设置将应用到所有转换的字幕文件\n• 建议选择支持中文的字体以确保正确显示")
        font_info.setStyleSheet("color: #A0A0A0; font-size: 12px;")
        font_layout.addWidget(font_info)

        main_layout.addWidget(font_card)

        # 关于卡片 - 减少内边距和内容
        about_card = ModernCard()
        about_layout = QVBoxLayout(about_card)
        about_layout.setContentsMargins(12, 12, 12, 12)  # 从20减少到12
        about_layout.setSpacing(6)  # 减少间距

        about_title = ModernLabel("关于", "subtitle")
        about_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                margin: 4px 0;
            }
        """)
        about_layout.addWidget(about_title)

        about_text = ModernLabel(
            "字幕格式转换器 - 支持 SRT/VTT/ASS 格式转换\n\n"
            "主要功能：批量处理、自定义样式、繁体转换\n"
            "使用方法：添加文件 → 配置选项 → 开始转换"
        )
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)

        main_layout.addWidget(about_card)
        main_layout.addStretch()

        self.setWidget(main_widget)

        # 初始化显示
        self.update_output_dir_display()
        self.update_font_display()

    def choose_output_directory(self):
        """选择输出目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择输出目录",
            self.parent.main_interface.output_directory or os.path.expanduser("~")
        )
        if directory:
            self.parent.main_interface.output_directory = directory
            self.parent.save_settings()
            self.update_output_dir_display()
            self.parent.main_interface.show_info_bar("设置成功", f"输出目录已设置为: {directory}", "success")

    def clear_output_directory(self):
        """清除输出目录设置"""
        self.parent.main_interface.output_directory = ""
        self.parent.save_settings()
        self.update_output_dir_display()
        self.parent.main_interface.show_info_bar("设置清除", "已清除输出目录设置，将使用原文件目录", "success")

    def update_output_dir_display(self):
        """更新输出目录显示"""
        output_dir = self.parent.main_interface.output_directory
        if output_dir:
            if len(output_dir) > 50:
                display_dir = "..." + output_dir[-47:]
            else:
                display_dir = output_dir
            self.output_dir_display.setText(display_dir)
            self.output_dir_display.setStyleSheet("color: #FFFFFF; font-weight: bold;")
            self.clear_output_dir_btn.setEnabled(True)
        else:
            self.output_dir_display.setText("未设置（使用原文件目录）")
            self.output_dir_display.setStyleSheet("color: #B0B0B0; font-style: italic; font-weight: normal; font-size: 13px;")
            self.clear_output_dir_btn.setEnabled(False)

    def choose_color(self, color_type):
        """选择颜色"""
        color = QColorDialog.getColor()
        if color.isValid():
            color_value = f"{color.blue():02x}{color.green():02x}{color.red():02x}"
            if color_type == 'subtitle':
                self.parent.subtitle_color = f'H00{color_value.upper()}'
                self.parent.main_interface.subtitle_color = self.parent.subtitle_color
            else:
                self.parent.outline_color = f'H00{color_value.upper()}'
                self.parent.main_interface.outline_color = self.parent.outline_color

            self.parent.save_subtitle_configs()
            self.update_color_buttons()
            self.config_changed.emit()

    def update_color_buttons(self):
        """更新颜色按钮显示"""
        subtitle_color = f'#{self.parent.subtitle_color[3:5]}{self.parent.subtitle_color[5:7]}{self.parent.subtitle_color[7:9]}'
        outline_color = f'#{self.parent.outline_color[3:5]}{self.parent.outline_color[5:7]}{self.parent.outline_color[7:9]}'

        self.subtitle_color_button.setStyleSheet(f'background-color: {subtitle_color}; color: white;')
        self.outline_color_button.setStyleSheet(f'background-color: {outline_color}; color: white;')

    def choose_font(self):
        """选择字体"""
        current_font = QFont()
        current_font.setFamily(self.parent.font_family)
        current_font.setPointSize(self.parent.font_size)

        font, ok = QFontDialog.getFont(current_font, self)

        if ok:
            self.parent.font_family = font.family()
            self.parent.font_size = font.pointSize()
            self.parent.save_settings()
            self.update_font_display()
            self.parent.main_interface.show_info_bar("字体设置成功", f"字体已设置为: {font.family()}, {font.pointSize()}pt", "success")

    def reset_font(self):
        """重置字体为默认值"""
        default_family = "方正粗圆_GBK"
        default_size = 70

        self.parent.font_family = default_family
        self.parent.font_size = default_size
        self.parent.save_settings()
        self.update_font_display()
        self.parent.main_interface.show_info_bar("字体重置成功", f"字体已重置为默认: {default_family}, {default_size}pt", "success")

    def update_font_display(self):
        """更新字体显示"""
        font_text = f"{self.parent.font_family}, {self.parent.font_size}pt"
        self.font_display.setText(font_text)

        # 更新预览字体
        preview_font = QFont(self.parent.font_family, 16)
        self.font_preview.setFont(preview_font)

class SubtitleConfigDialog(QDialog):
    """字幕配置对话框"""
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('插入ASS语句配置')
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: white;
            }
            QLineEdit, QTextEdit, QTimeEdit {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
            QLabel {
                color: white;
            }
        """)
        self.config = config or {}

        layout = QFormLayout(self)

        # 创建字段
        self.fields = {
            'name': QLineEdit(self.config.get('name', '')),
            'start_time': QTimeEdit(),
            'end_time': QTimeEdit(),
            'ass_statement': QTextEdit(self.config.get('ass_statement', ''))
        }

        # 标签
        labels = {
            'name': '配置名称',
            'start_time': '开始时间',
            'end_time': '结束时间',
            'ass_statement': 'ASS语句'
        }

        # 设置时间格式
        for field, widget in self.fields.items():
            if isinstance(widget, QTimeEdit):
                widget.setDisplayFormat('HH:mm:ss.zzz')
                if field == 'start_time':
                    widget.setTime(QTime.fromString(
                        self.config.get('start_time', '00:00:00.000'), 'HH:mm:ss.zzz'))
                else:
                    widget.setTime(QTime.fromString(
                        self.config.get('end_time', '00:00:05.000'), 'HH:mm:ss.zzz'))
            layout.addRow(labels[field], widget)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Ok).setText('确定')
        buttons.button(QDialogButtonBox.Cancel).setText('取消')
        layout.addRow(buttons)

    def get_config(self):
        return {
            'name': self.fields['name'].text(),
            'start_time': self.fields['start_time'].time().toString('HH:mm:ss.zzz'),
            'end_time': self.fields['end_time'].time().toString('HH:mm:ss.zzz'),
            'ass_statement': self.fields['ass_statement'].toPlainText()
        }

class WorkerSignals(QObject):
    """工作线程信号"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

class ConvertWorker(QRunnable):
    """转换工作线程"""
    def __init__(self, srt_file, ass_file, insert_options, subtitle_configs,
                 subtitle_color, outline_color, delete_original, convert_to_china,
                 font_family, font_size, api_priority=True):
        super().__init__()
        self.srt_file, self.ass_file = srt_file, ass_file
        self.insert_options, self.subtitle_configs = insert_options, subtitle_configs
        self.subtitle_color = f'&{subtitle_color}'
        self.outline_color = f'&{outline_color}'
        self.delete_original = delete_original
        self.convert_to_china = convert_to_china
        self.font_family = font_family
        self.font_size = font_size
        self.api_priority = api_priority
        self.signals = WorkerSignals()
        self.china_convert_failed = False  # 跟踪繁体转换状态

    def convert_to_china_text(self, text, api_priority=True):
        """繁体中文转换 - 支持API优先设置"""
        if not text or not text.strip():
            return text, False  # 返回转换结果和是否成功的标志

        # 根据API优先设置决定转换顺序
        if api_priority:
            # API优先：先尝试在线API，再尝试本地OpenCC
            result = self._try_api_convert(text)
            if result[1]:  # 如果API转换成功
                return result
            # API失败，尝试本地转换
            return self._try_opencc_convert(text)
        else:
            # OpenCC优先：先尝试本地OpenCC，再尝试在线API
            result = self._try_opencc_convert(text)
            if result[1]:  # 如果OpenCC转换成功
                return result
            # OpenCC失败，尝试API转换
            return self._try_api_convert(text)

    def _try_opencc_convert(self, text):
        """尝试使用OpenCC本地转换"""
        try:
            import opencc
            converter = opencc.OpenCC('t2s')  # 繁体转简体
            converted = converter.convert(text)
            return converted, True  # 转换成功
        except ImportError:
            return text, False  # OpenCC未安装
        except Exception:
            return text, False  # 转换失败

    def _try_api_convert(self, text):
        """尝试使用在线API转换"""
        # 使用在线API转换
        url = 'https://api.zhconvert.org/convert'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'origin': 'http://zhconvert.org',
            'referer': 'http://zhconvert.org/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
        }

        data = {
            'text': text,
            'converter': 'China',
            'modules': '{"ChineseVariant":"1"}',
            'jpTextConversionStrategy': 'none',
            'jpStyleConversionStrategy': 'none',  # 修复：使用字符串而不是布尔值
            'diffEnable': False,
            'outputFormat': 'json'
        }

        # 尝试多种网络配置
        proxy_configs = [
            None,  # 不使用代理
            {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'},  # 常见代理端口
            {'http': 'http://127.0.0.1:1080', 'https': 'http://127.0.0.1:1080'},  # 另一个常见端口
        ]

        for proxies in proxy_configs:
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    proxies=proxies,
                    timeout=10  # 减少超时时间
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 0:
                        converted_text = result.get('data', {}).get('text', text)
                        if converted_text and converted_text.strip():
                            return converted_text, True  # 转换成功
                        else:
                            return text, False  # 如果转换结果为空，返回原文
                    else:
                        continue  # 尝试下一个配置
                else:
                    continue  # 尝试下一个配置

            except requests.exceptions.RequestException:
                continue  # 尝试下一个配置
            except Exception:
                continue  # 尝试下一个配置

        # 如果所有方法都失败，返回原文本
        return text, False  # 转换失败

    def run(self):
        try:
            # 加载字幕文件
            if self.srt_file.endswith('.srt'):
                subs = pysubs2.load(self.srt_file, encoding='utf-8')
            elif self.srt_file.endswith('.vtt'):
                subs = pysubs2.load(self.srt_file, encoding='utf-8', format='vtt')
            elif self.srt_file.endswith('.ass'):
                subs = pysubs2.load(self.srt_file, encoding='utf-8')
            else:
                raise ValueError('Unsupported file format')

            # 设置样式信息
            if not self.srt_file.endswith('.ass'):
                subs.info = {
                    'Title': 'Default Aegisub file',
                    'ScriptType': 'v4.00+',
                    'WrapStyle': '0',
                    'ScaledBorderAndShadow': 'yes',
                    'YCbCr Matrix': 'TV.601',
                    'PlayResX': '1920',
                    'PlayResY': '1080'
                }

                subs.styles['Default'] = pysubs2.SSAStyle(
                    fontname=self.font_family,
                    fontsize=self.font_size,
                    primarycolor=self.subtitle_color,
                    outlinecolor=self.outline_color,
                    shadow=1.0
                )
            else:
                if 'PlayResX' not in subs.info or not subs.info['PlayResX']:
                    subs.info['PlayResX'] = '1920'
                if 'PlayResY' not in subs.info or not subs.info['PlayResY']:
                    subs.info['PlayResY'] = '1080'

                if 'Default' in subs.styles:
                    default_style = subs.styles['Default']
                    default_style.primarycolor = self.subtitle_color
                    default_style.outlinecolor = self.outline_color
                else:
                    subs.styles['Default'] = pysubs2.SSAStyle(
                        fontname=self.font_family,
                        fontsize=self.font_size,
                        primarycolor=self.subtitle_color,
                        outlinecolor=self.outline_color,
                        shadow=1.0
                    )

            # 繁体转换
            if self.convert_to_china:
                try:
                    # 收集所有文本
                    all_texts = []
                    for event in subs.events:
                        if event.text and event.text.strip():
                            all_texts.append(event.text)
                        else:
                            all_texts.append("")  # 保持空文本的位置

                    if all_texts:
                        # 合并文本进行转换
                        combined_text = '\n'.join(all_texts)
                        converted_text, success = self.convert_to_china_text(combined_text, self.api_priority)

                        if success and converted_text:
                            converted_texts = converted_text.split('\n')

                            # 确保转换后的文本数量匹配
                            if len(converted_texts) == len(all_texts):
                                for event, text in zip(subs.events, converted_texts):
                                    event.text = text if text else event.text
                            else:
                                # 如果数量不匹配，逐个转换
                                for event in subs.events:
                                    if event.text and event.text.strip():
                                        try:
                                            converted, individual_success = self.convert_to_china_text(event.text, self.api_priority)
                                            if individual_success:
                                                event.text = converted
                                            else:
                                                self.china_convert_failed = True
                                        except:
                                            self.china_convert_failed = True
                        else:
                            self.china_convert_failed = True

                except Exception as e:
                    # 繁体转换失败，但不影响整个转换过程
                    self.china_convert_failed = True
                    pass

            # 插入自定义字幕
            for insert_option in self.insert_options:
                if insert_option != '不插入字幕':
                    config = next((c for c in self.subtitle_configs if c['name'] == insert_option), None)
                    if config:
                        start = pysubs2.make_time(
                            int(config['start_time'][:2]),
                            int(config['start_time'][3:5]),
                            int(config['start_time'][6:8]),
                            int(config['start_time'][9:12])
                        )
                        end = pysubs2.make_time(
                            int(config['end_time'][:2]),
                            int(config['end_time'][3:5]),
                            int(config['end_time'][6:8]),
                            int(config['end_time'][9:12])
                        )
                        subs.events.append(pysubs2.SSAEvent(
                            start=start,
                            end=end,
                            text=config['ass_statement']
                        ))

            # 保存文件
            subs.save(self.ass_file)

            # 删除原文件
            if self.delete_original:
                os.remove(self.srt_file)

            # 构建完成消息
            status_msg = f"已保存到: {self.ass_file}"
            if self.convert_to_china and self.china_convert_failed:
                status_msg += " (繁体转换失败，保持原文本)"
            self.signals.finished.emit(status_msg)

        except Exception as e:
            self.signals.error.emit(str(e))

class SrtToAssConverter(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.threadpool = QThreadPool()
        self.load_subtitle_configs()
        self.conversion_count = self.total_conversions = 0
        self.delete_original_after_convert = False
        self.convert_to_china = False
        self.api_priority = True  # 默认API优先

        # 初始化字体设置
        self.font_family = "方正粗圆_GBK"
        self.font_size = 70
        self.initUI()
        self.load_settings()
        self.init_tray()

    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle('字幕格式转换器')
        self.setMinimumSize(900, 700)
        self.resize(1100, 800)

        # 设置深色主题
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2B2B2B;
                color: #FFFFFF;
            }
        """)

        # 设置窗口图标
        try:
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
            else:
                icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except:
            pass

        # 创建自定义左侧标签页
        self.tab_widget = CustomSideTabWidget()
        self.setCentralWidget(self.tab_widget)

        # 创建主界面
        self.main_interface = MainInterface(self)
        self.tab_widget.addTab(self.main_interface, "主页")

        # 创建设置界面
        self.settings_interface = SettingsInterface(self)
        self.tab_widget.addTab(self.settings_interface, "设置")

        # 连接信号
        self.main_interface.subtitle_configs = self.subtitle_configs
        self.main_interface.subtitle_color = self.subtitle_color
        self.main_interface.outline_color = self.outline_color
        self.main_interface.delete_original_after_convert = self.delete_original_after_convert
        self.main_interface.convert_to_china = self.convert_to_china

        # 连接转换信号
        self.main_interface.convert_requested.connect(self.start_conversion)
        self.settings_interface.config_changed.connect(self.on_config_changed)

        # 连接页面切换信号
        self.tab_widget.currentChanged.connect(self.on_page_changed)

        # 初始化配置列表
        self.main_interface.refresh_config_list()
        self.settings_interface.update_color_buttons()

    def on_page_changed(self, index):
        """页面切换时的处理"""
        if index == 1:  # 设置页面
            self.settings_interface.update_output_dir_display()
            self.settings_interface.update_font_display()

    def start_conversion(self, files, insert_options, subtitle_color, outline_color, delete_original, convert_to_china):
        """开始转换处理"""
        try:
            # 检查输出目录设置
            if not self.main_interface.output_directory:
                output_dir = QFileDialog.getExistingDirectory(
                    self, "选择输出目录", os.path.expanduser("~")
                )
                if not output_dir:
                    self.main_interface.show_info_bar("转换取消", "未选择输出目录，转换已取消", "warning")
                    return

                self.main_interface.output_directory = output_dir
                self.save_settings()
                if hasattr(self, 'settings_interface'):
                    self.settings_interface.update_output_dir_display()
                self.main_interface.show_info_bar("目录已设置", f"输出目录已设置为: {output_dir}", "success")

            self.total_conversions = len(files)
            self.conversion_count = 0

            # 记录输出信息
            self.main_interface.output_directory_used = self.main_interface.output_directory
            self.main_interface.output_files = []

            for file_path in files:
                filename = os.path.splitext(os.path.basename(file_path))[0] + '.ass'
                ass_file = os.path.join(self.main_interface.output_directory, filename)
                self.main_interface.output_files.append(ass_file)

                worker = ConvertWorker(
                    file_path, ass_file, insert_options, self.subtitle_configs,
                    subtitle_color, outline_color, delete_original, convert_to_china,
                    self.font_family, self.font_size, self.main_interface.api_priority
                )

                worker.signals.finished.connect(self.on_conversion_finished)
                worker.signals.error.connect(self.on_conversion_error)
                self.threadpool.start(worker)

            # 禁用转换按钮
            self.main_interface.convert_button.setEnabled(False)
            self.main_interface.convert_button.setText("转换中...")

            # 显示开始转换信息
            self.main_interface.show_info_bar("开始转换", f"正在转换 {len(files)} 个文件...", "info")

        except Exception as e:
            self.main_interface.show_info_bar("转换失败", f"转换启动失败: {str(e)}", "error")

    def on_conversion_finished(self, _):
        """转换完成处理"""
        self.conversion_count += 1

        if self.conversion_count == self.total_conversions:
            # 所有文件转换完成
            self.main_interface.convert_button.setEnabled(True)
            self.main_interface.convert_button.setText("开始转换")

            # 显示转换完成消息
            content = f"所有文件已转换完成！保存在: {self.main_interface.output_directory_used}"
            self.main_interface.show_info_bar("转换完成", content, "success")

            # 清空文件列表
            self.main_interface.clear_all_files()

            # 显示输出位置信息
            self.show_output_location_info()

    def show_output_location_info(self):
        """显示输出位置信息"""
        try:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("转换完成")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: white;
                }
                QMessageBox QPushButton {
                    background-color: rgba(0, 120, 212, 0.8);
                    border: 1px solid rgba(0, 120, 212, 1.0);
                    border-radius: 4px;
                    color: white;
                    padding: 6px 12px;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: rgba(0, 120, 212, 1.0);
                }
            """)

            output_dir = self.main_interface.output_directory_used
            msg_box.setText(f"所有文件已保存到:\n{output_dir}")
            msg_box.setInformativeText("选择要执行的操作：")

            open_folder_btn = msg_box.addButton("打开文件夹", QMessageBox.ActionRole)
            show_list_btn = msg_box.addButton("显示文件列表", QMessageBox.ActionRole)
            msg_box.addButton("取消", QMessageBox.RejectRole)
            msg_box.setDefaultButton(open_folder_btn)

            msg_box.exec_()

            if msg_box.clickedButton() == open_folder_btn:
                self.open_folder(output_dir)
            elif msg_box.clickedButton() == show_list_btn:
                self.show_output_files_list()

        except Exception as e:
            print(f"无法显示输出位置信息: {e}")

    def open_folder(self, folder_path):
        """打开指定文件夹"""
        try:
            import subprocess
            import platform

            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            elif system == "Windows":
                subprocess.run(["explorer", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            print(f"无法打开文件夹 {folder_path}: {e}")

    def show_output_files_list(self):
        """显示输出文件列表"""
        try:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("转换结果文件列表")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: white;
                }
            """)
            msg_box.setText("以下是所有转换后的文件:")

            files_text = "\n".join([f"• {os.path.basename(file)}" for file in self.main_interface.output_files])
            msg_box.setDetailedText(files_text)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
        except Exception as e:
            print(f"无法显示文件列表: {e}")

    def on_conversion_error(self, error_msg):
        """转换错误处理"""
        self.conversion_count += 1
        self.main_interface.show_info_bar("转换错误", f"转换失败: {error_msg}", "error")

        if self.conversion_count == self.total_conversions:
            self.main_interface.convert_button.setEnabled(True)
            self.main_interface.convert_button.setText("开始转换")

    def on_config_changed(self):
        """配置改变处理"""
        self.main_interface.subtitle_color = self.subtitle_color
        self.main_interface.outline_color = self.outline_color

    def init_tray(self):
        """初始化系统托盘"""
        if hasattr(sys, '_MEIPASS'):
            application_path = sys._MEIPASS
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(application_path, 'icon.ico')

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icon_path))

        self.tray_menu = QMenu()
        show_action = self.tray_menu.addAction('显示主窗口')
        quit_action = self.tray_menu.addAction('退出程序')

        show_action.triggered.connect(self.show_main_window)
        quit_action.triggered.connect(self.quit_application)
        self.tray_icon.activated.connect(self.tray_icon_clicked)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

    def show_main_window(self):
        """显示主窗口"""
        self.show()
        self.setWindowState(Qt.WindowActive)
        self.activateWindow()
        self.raise_()

    def quit_application(self):
        """退出应用程序"""
        self.tray_icon.hide()
        QApplication.instance().quit()

    def tray_icon_clicked(self, reason):
        """托盘图标点击事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_main_window()

    def closeEvent(self, event):
        """关闭事件处理"""
        try:
            if self.tray_icon and self.tray_icon.isVisible():
                self.hide()
                self.tray_icon.showMessage(
                    '提示',
                    '程序已最小化到系统托盘，双击托盘图标可以重新打开窗口',
                    QSystemTrayIcon.Information,
                    2000
                )
                event.ignore()
            else:
                event.accept()
        except Exception as e:
            print(f'关闭事件处理错误: {str(e)}')
            event.accept()

    def load_subtitle_configs(self):
        """加载字幕配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.subtitle_configs = config.get('subtitle_configs', [])
                    self.subtitle_color = config.get('subtitle_color', 'H00FFFFFF')
                    self.outline_color = config.get('outline_color', 'H00000000')
            except json.JSONDecodeError:
                print('Error decoding JSON. Using default values.')
                self.subtitle_configs = []
                self.subtitle_color = 'H00FFFFFF'
                self.outline_color = 'H00000000'
        else:
            self.subtitle_configs = []
            self.subtitle_color = 'H00FFFFFF'
            self.outline_color = 'H00000000'

    def save_subtitle_configs(self):
        """保存字幕配置"""
        try:
            config = {
                'subtitle_configs': self.subtitle_configs,
                'subtitle_color': self.subtitle_color,
                'outline_color': self.outline_color
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def load_settings(self):
        """加载程序设置"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.main_interface.output_directory = settings.get('output_directory', '')
                    self.font_family = settings.get('font_family', '方正粗圆_GBK')
                    self.font_size = settings.get('font_size', 70)
            else:
                self.font_family = '方正粗圆_GBK'
                self.font_size = 70
        except Exception as e:
            print(f"加载设置失败: {e}")
            self.main_interface.output_directory = ''
            self.font_family = '方正粗圆_GBK'
            self.font_size = 70

    def save_settings(self):
        """保存程序设置"""
        try:
            settings = {
                'output_directory': self.main_interface.output_directory,
                'font_family': self.font_family,
                'font_size': self.font_size
            }
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存设置失败: {e}")

def main():
    """主函数"""
    try:
        # 创建应用程序
        app = QApplication(sys.argv)

        # 设置应用程序属性
        app.setApplicationName("SRT转ASS字幕转换器")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("SubtitleConverter")

        # 设置默认字体
        font = QFont()
        if sys.platform == "darwin":  # macOS
            font.setFamily("PingFang SC")
        elif sys.platform == "win32":  # Windows
            font.setFamily("Microsoft YaHei")
        else:  # Linux
            font.setFamily("Noto Sans CJK SC")
        font.setPointSize(10)
        app.setFont(font)

        # 设置深色调色板
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(43, 43, 43))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        app.setPalette(palette)

        # 创建并显示主窗口
        window = SrtToAssConverter()
        window.show()

        # 启动应用程序
        sys.exit(app.exec_())

    except Exception as e:
        print(f'程序启动错误: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
