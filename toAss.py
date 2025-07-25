#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRT 转 ASS 字幕转换器
基于字节码分析重构的代码
"""

import sys
import os
import json
import pysubs2
import requests
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem, QCheckBox, QLabel,
                             QDialog, QFormLayout, QLineEdit, QTimeEdit, QTextEdit, QDialogButtonBox,
                             QFileDialog, QColorDialog, QAbstractItemView, QSystemTrayIcon, QMenu, QMessageBox,
                             QFontDialog, QComboBox, QSpinBox)
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject, QTranslator, QLibraryInfo, QTime
from PyQt5.QtGui import QFont, QIcon
from qfluentwidgets import (PushButton, Theme, setTheme, InfoBar, InfoBarPosition, FluentIcon as FIF,
                           CardWidget, BodyLabel, SubtitleLabel, TitleLabel,
                           ScrollArea, VBoxLayout, MSFluentWindow)

CONFIG_FILE = 'sub.json'
SETTINGS_FILE = 'settings.json'

class DragDropListWidget(QListWidget):
    """支持拖拽的文件列表组件"""
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否包含支持的文件类型
            urls = event.mimeData().urls()
            valid_files = []
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.srt', '.vtt', '.ass')):
                    valid_files.append(file_path)

            if valid_files:
                event.acceptProposedAction()
                # 添加视觉反馈
                self.setStyleSheet("""
                    QListWidget {
                        border: 2px solid #00D4FF;
                        border-radius: 8px;
                        background-color: rgba(0, 212, 255, 0.1);
                        padding: 10px;
                        font-size: 12px;
                    }
                    QListWidget::item {
                        padding: 8px;
                        margin: 2px;
                        border-radius: 4px;
                        background-color: rgba(255, 255, 255, 0.1);
                    }
                    QListWidget::item:selected {
                        background-color: rgba(0, 120, 212, 0.6);
                    }
                    QListWidget::item:hover {
                        background-color: rgba(255, 255, 255, 0.15);
                    }
                """)
            else:
                event.ignore()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            # 检查是否包含支持的文件类型
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
        # 恢复原始样式
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #666666;
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.05);
                padding: 10px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                margin: 2px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.1);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.6);
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.15);
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

        # 恢复原始样式
        self.dragLeaveEvent(event)

class MainInterface(ScrollArea):
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
        self.output_directory = ""  # 输出目录配置

        self.setupUI()

    def setupUI(self):
        """设置主界面UI"""
        self.setObjectName("mainInterface")
        self.setWidgetResizable(True)

        # 主容器
        main_widget = QWidget()
        main_layout = VBoxLayout(main_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title = TitleLabel("字幕格式转换器")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # 文件区域卡片
        file_card = CardWidget()
        file_layout = VBoxLayout(file_card)
        file_layout.setContentsMargins(20, 20, 20, 20)

        file_title = SubtitleLabel("文件列表")
        file_layout.addWidget(file_title)

        # 文件列表 - 使用自定义的拖拽列表
        self.file_list = DragDropListWidget()
        self.file_list.setMinimumHeight(200)
        self.file_list.setAcceptDrops(True)
        self.file_list.setDragDropMode(QAbstractItemView.DropOnly)
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # 连接文件拖拽信号
        self.file_list.files_dropped.connect(self.handle_dropped_files)

        # 设置文件列表样式
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 2px dashed #666666;
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.05);
                padding: 10px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                margin: 2px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.1);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.6);
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)

        # 添加占位符文本
        if self.file_list.count() == 0:
            placeholder_item = QListWidgetItem("拖拽 SRT、VTT 或 ASS 文件到此处，或点击'添加文件'按钮")
            placeholder_item.setFlags(Qt.NoItemFlags)
            placeholder_item.setTextAlignment(Qt.AlignCenter)
            self.file_list.addItem(placeholder_item)

        file_layout.addWidget(self.file_list)

        # 文件操作按钮
        file_buttons_layout = QHBoxLayout()

        add_files_btn = PushButton("添加文件")
        add_files_btn.setIcon(FIF.ADD)
        add_files_btn.clicked.connect(self.add_files)
        file_buttons_layout.addWidget(add_files_btn)

        remove_files_btn = PushButton("删除选中")
        remove_files_btn.setIcon(FIF.DELETE)
        remove_files_btn.clicked.connect(self.remove_selected_files)
        file_buttons_layout.addWidget(remove_files_btn)

        clear_files_btn = PushButton("清除全部")
        clear_files_btn.setIcon(FIF.CANCEL)
        clear_files_btn.clicked.connect(self.clear_all_files)
        file_buttons_layout.addWidget(clear_files_btn)

        file_buttons_layout.addStretch()
        file_layout.addLayout(file_buttons_layout)

        main_layout.addWidget(file_card)

        # 配置区域
        config_layout = QHBoxLayout()

        # 字幕配置卡片
        subtitle_card = CardWidget()
        subtitle_layout = VBoxLayout(subtitle_card)
        subtitle_layout.setContentsMargins(20, 20, 20, 20)

        subtitle_title = SubtitleLabel("字幕配置")
        subtitle_layout.addWidget(subtitle_title)

        self.insert_options = CheckableListWidget()
        self.insert_options.setMaximumHeight(150)
        subtitle_layout.addWidget(self.insert_options)

        # 字幕配置按钮
        subtitle_buttons_layout = QHBoxLayout()

        add_config_btn = PushButton("添加")
        add_config_btn.setIcon(FIF.ADD)
        add_config_btn.clicked.connect(self.add_subtitle_config)
        subtitle_buttons_layout.addWidget(add_config_btn)

        edit_config_btn = PushButton("编辑")
        edit_config_btn.setIcon(FIF.EDIT)
        edit_config_btn.clicked.connect(self.edit_subtitle_config)
        subtitle_buttons_layout.addWidget(edit_config_btn)

        delete_config_btn = PushButton("删除")
        delete_config_btn.setIcon(FIF.DELETE)
        delete_config_btn.clicked.connect(self.delete_subtitle_config)
        subtitle_buttons_layout.addWidget(delete_config_btn)

        subtitle_layout.addLayout(subtitle_buttons_layout)
        config_layout.addWidget(subtitle_card)

        # 选项卡片
        options_card = CardWidget()
        options_layout = VBoxLayout(options_card)
        options_layout.setContentsMargins(20, 20, 20, 20)

        options_title = SubtitleLabel("转换选项")
        options_layout.addWidget(options_title)

        # 删除原文件选项
        self.delete_original_checkbox = QCheckBox('转换后删除原文件')
        self.delete_original_checkbox.setChecked(True)
        self.delete_original_checkbox.stateChanged.connect(self.on_delete_original_changed)
        options_layout.addWidget(self.delete_original_checkbox)

        # 繁体中国化选项
        self.convert_to_china_checkbox = QCheckBox('繁体中国化')
        self.convert_to_china_checkbox.stateChanged.connect(self.on_convert_to_china_changed)
        options_layout.addWidget(self.convert_to_china_checkbox)

        # API优先选项
        self.api_priority_checkbox = QCheckBox('API优先转换')
        self.api_priority_checkbox.setChecked(True)  # 默认选中API优先
        self.api_priority_checkbox.stateChanged.connect(self.on_api_priority_changed)
        options_layout.addWidget(self.api_priority_checkbox)

        options_layout.addStretch()
        config_layout.addWidget(options_card)

        main_layout.addLayout(config_layout)

        # 转换按钮
        convert_layout = QHBoxLayout()
        convert_layout.addStretch()

        self.convert_button = PushButton("开始转换")
        self.convert_button.setIcon(FIF.SYNC)
        self.convert_button.clicked.connect(self.start_convert)
        self.convert_button.setMinimumSize(120, 40)
        convert_layout.addWidget(self.convert_button)

        main_layout.addLayout(convert_layout)
        main_layout.addStretch()

        self.setWidget(main_widget)

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
                InfoBar.success(
                    title="文件添加成功",
                    content=f"已添加 {added_count} 个文件",
                    orient=Qt.Horizontal, isClosable=True,
                    position=InfoBarPosition.TOP, duration=2000, parent=self
                )

    def add_files(self):
        """添加文件"""
        try:
            # 获取用户主目录作为默认路径
            import os
            home_dir = os.path.expanduser("~")

            files, _ = QFileDialog.getOpenFileNames(
                self,
                '选择SRT、VTT或ASS文件',
                home_dir,  # 默认目录
                'Subtitle Files (*.srt *.vtt *.ass);;SRT Files (*.srt);;VTT Files (*.vtt);;ASS Files (*.ass);;All Files (*)'
            )

            if not files:  # 用户取消了选择
                return

            # 如果有占位符，先清除
            if self.file_list.count() == 1:
                first_item = self.file_list.item(0)
                if first_item and first_item.flags() == Qt.NoItemFlags:
                    self.file_list.clear()

            # 添加选择的文件
            for file in files:
                # 检查文件是否已存在
                existing_files = [self.file_list.item(i).text()
                                for i in range(self.file_list.count())]
                if file not in existing_files:
                    self.file_list.addItem(file)

            # 显示成功信息
            if files:
                InfoBar.success(
                    title="文件添加成功",
                    content=f"已添加 {len(files)} 个文件",
                    orient=Qt.Horizontal, isClosable=True,
                    position=InfoBarPosition.TOP, duration=2000, parent=self
                )

        except Exception as e:
            # 显示错误信息
            InfoBar.error(
                title="添加文件失败",
                content=f"错误: {str(e)}",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=3000, parent=self
            )

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
            if item and item.flags() != Qt.NoItemFlags:  # 排除占位符
                files.append(item.text())

        if len(files) == 0:
            InfoBar.warning(
                title="警告", content="请先添加要转换的文件",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self
            )
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
            # 同时更新主界面和主程序的配置
            self.subtitle_configs.append(config)
            self.parent.subtitle_configs.append(config)
            self.insert_options.addCheckableItem(config['name'])
            self.parent.save_subtitle_configs()

    def edit_subtitle_config(self):
        """编辑字幕配置"""
        checked_items = self.insert_options.getCheckedItems()
        if len(checked_items) != 1 or checked_items[0] == '不插入字幕':
            InfoBar.warning(
                title="提示", content="请选择一个配置项进行编辑",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self
            )
            return

        config_name = checked_items[0]
        config = next((c for c in self.subtitle_configs if c['name'] == config_name), None)
        if config:
            dialog = SubtitleConfigDialog(config, self)
            if dialog.exec_():
                new_config = dialog.get_config()
                # 同时更新主界面和主程序的配置
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
            InfoBar.warning(
                title="提示", content="请选择一个配置项进行删除",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self
            )
            return

        config_name = checked_items[0]
        # 同时更新主界面和主程序的配置
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

class SettingsInterface(ScrollArea):
    """设置界面"""
    config_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setupUI()

    def setupUI(self):
        """设置界面UI"""
        self.setObjectName("settingsInterface")
        self.setWidgetResizable(True)

        # 主容器
        main_widget = QWidget()
        main_layout = VBoxLayout(main_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title = TitleLabel("设置")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # 输出目录设置卡片
        output_card = CardWidget()
        output_layout = VBoxLayout(output_card)
        output_layout.setContentsMargins(20, 20, 20, 20)

        output_title = SubtitleLabel("输出目录设置")
        output_layout.addWidget(output_title)

        # 输出目录选择
        output_dir_layout = QHBoxLayout()
        output_dir_label = BodyLabel("输出目录:")
        output_dir_layout.addWidget(output_dir_label)

        self.output_dir_display = BodyLabel("未设置（使用原文件目录）")
        self.output_dir_display.setStyleSheet("color: #CCCCCC; font-style: italic; font-weight: normal;")
        output_dir_layout.addWidget(self.output_dir_display)
        output_dir_layout.addStretch()

        self.choose_output_dir_btn = PushButton("选择目录")
        self.choose_output_dir_btn.clicked.connect(self.choose_output_directory)
        output_dir_layout.addWidget(self.choose_output_dir_btn)

        self.clear_output_dir_btn = PushButton("清除设置")
        self.clear_output_dir_btn.clicked.connect(self.clear_output_directory)
        output_dir_layout.addWidget(self.clear_output_dir_btn)

        output_layout.addLayout(output_dir_layout)

        # 输出目录说明
        output_info = BodyLabel("• 未设置时：文件保存在原文件相同目录\n• 已设置时：所有文件统一保存到指定目录")
        output_info.setStyleSheet("color: #888888; font-size: 12px;")
        output_layout.addWidget(output_info)

        main_layout.addWidget(output_card)

        # 颜色设置卡片
        color_card = CardWidget()
        color_layout = VBoxLayout(color_card)
        color_layout.setContentsMargins(20, 20, 20, 20)

        color_title = SubtitleLabel("字幕颜色设置")
        color_layout.addWidget(color_title)

        # 字幕颜色
        subtitle_color_layout = QHBoxLayout()
        subtitle_color_label = BodyLabel("字幕颜色:")
        subtitle_color_layout.addWidget(subtitle_color_label)

        self.subtitle_color_button = PushButton("选择颜色")
        self.subtitle_color_button.clicked.connect(lambda: self.choose_color('subtitle'))
        subtitle_color_layout.addWidget(self.subtitle_color_button)
        subtitle_color_layout.addStretch()

        color_layout.addLayout(subtitle_color_layout)

        # 边框颜色
        outline_color_layout = QHBoxLayout()
        outline_color_label = BodyLabel("边框颜色:")
        outline_color_layout.addWidget(outline_color_label)

        self.outline_color_button = PushButton("选择颜色")
        self.outline_color_button.clicked.connect(lambda: self.choose_color('outline'))
        outline_color_layout.addWidget(self.outline_color_button)
        outline_color_layout.addStretch()

        color_layout.addLayout(outline_color_layout)
        main_layout.addWidget(color_card)

        # 字体设置卡片
        font_card = CardWidget()
        font_layout = VBoxLayout(font_card)
        font_layout.setContentsMargins(20, 20, 20, 20)

        font_title = SubtitleLabel("字体设置")
        font_layout.addWidget(font_title)

        # 字体选择
        font_selection_layout = QHBoxLayout()
        font_label = BodyLabel("字幕字体:")
        font_selection_layout.addWidget(font_label)

        self.font_display = BodyLabel("方正粗圆_GBK, 70pt")
        self.font_display.setStyleSheet("color: #CCCCCC; font-style: italic; font-weight: normal;")
        font_selection_layout.addWidget(self.font_display)
        font_selection_layout.addStretch()

        self.choose_font_btn = PushButton("选择字体")
        self.choose_font_btn.clicked.connect(self.choose_font)
        font_selection_layout.addWidget(self.choose_font_btn)

        self.reset_font_btn = PushButton("重置默认")
        self.reset_font_btn.clicked.connect(self.reset_font)
        font_selection_layout.addWidget(self.reset_font_btn)

        font_layout.addLayout(font_selection_layout)

        # 字体预览
        self.font_preview = BodyLabel("字幕预览效果 Subtitle Preview 字幕样式测试")
        self.font_preview.setStyleSheet("""
            BodyLabel {
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 10px;
                background-color: rgba(0, 0, 0, 0.8);
                color: white;
                font-size: 16px;
                text-align: center;
            }
        """)
        self.font_preview.setAlignment(Qt.AlignCenter)
        font_layout.addWidget(self.font_preview)

        # 字体说明
        font_info = BodyLabel("• 字体设置将应用到所有转换的字幕文件\n• 建议选择支持中文的字体以确保正确显示")
        font_info.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        font_layout.addWidget(font_info)

        main_layout.addWidget(font_card)

        # 关于卡片
        about_card = CardWidget()
        about_layout = VBoxLayout(about_card)
        about_layout.setContentsMargins(20, 20, 20, 20)

        about_title = SubtitleLabel("关于")
        about_layout.addWidget(about_title)

        about_text = BodyLabel(
            "字幕格式转换器\n\n"
            "支持的格式转换：\n"
            "• SRT → ASS：标准字幕转高级字幕\n"
            "• VTT → ASS：网页字幕转高级字幕\n"
            "• ASS → ASS：修改现有ASS字幕样式\n\n"
            "功能特性：\n"
            "• 支持繁体中文转换\n"
            "• 支持自定义字幕样式和颜色\n"
            "• 支持批量文件处理\n"
            "• 保留ASS文件原有特效\n"
            "• 现代化的用户界面\n\n"
            "使用方法：\n"
            "1. 在主页添加要转换的字幕文件\n"
            "2. 配置转换选项和字幕样式\n"
            "3. 点击开始转换按钮"
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
            InfoBar.success(
                title="设置成功", content=f"输出目录已设置为: {directory}",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=3000, parent=self
            )

    def clear_output_directory(self):
        """清除输出目录设置"""
        self.parent.main_interface.output_directory = ""
        self.parent.save_settings()
        self.update_output_dir_display()
        InfoBar.success(
            title="设置清除", content="已清除输出目录设置，将使用原文件目录",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=3000, parent=self
        )

    def update_output_dir_display(self):
        """更新输出目录显示"""
        output_dir = self.parent.main_interface.output_directory
        if output_dir:
            # 显示目录路径，如果太长则截断
            if len(output_dir) > 50:
                display_dir = "..." + output_dir[-47:]
            else:
                display_dir = output_dir
            self.output_dir_display.setText(display_dir)
            self.output_dir_display.setStyleSheet("color: #FFFFFF; font-weight: bold;")
            self.clear_output_dir_btn.setEnabled(True)
        else:
            self.output_dir_display.setText("未设置（使用原文件目录）")
            self.output_dir_display.setStyleSheet("color: #CCCCCC; font-style: italic; font-weight: normal;")
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
        # 获取当前字体设置
        current_font = QFont()
        current_font.setFamily(self.parent.font_family)
        current_font.setPointSize(self.parent.font_size)

        # 打开字体选择对话框
        font, ok = QFontDialog.getFont(current_font, self)

        if ok:
            # 保存字体设置
            self.parent.font_family = font.family()
            self.parent.font_size = font.pointSize()
            print(f"选择新字体: {self.parent.font_family}, {self.parent.font_size}pt")
            self.parent.save_settings()

            # 更新显示
            self.update_font_display()

            InfoBar.success(
                title="字体设置成功",
                content=f"字体已设置为: {font.family()}, {font.pointSize()}pt",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=3000, parent=self
            )

    def reset_font(self):
        """重置字体为默认值"""
        # 重置为程序默认字体（方正粗圆_GBK）
        default_family = "方正粗圆_GBK"
        default_size = 70

        self.parent.font_family = default_family
        self.parent.font_size = default_size
        self.parent.save_settings()

        # 更新显示
        self.update_font_display()

        InfoBar.success(
            title="字体重置成功",
            content=f"字体已重置为默认: {default_family}, {default_size}pt",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=3000, parent=self
        )

    def update_font_display(self):
        """更新字体显示"""
        font_text = f"{self.parent.font_family}, {self.parent.font_size}pt"
        self.font_display.setText(font_text)

        # 更新预览字体
        preview_font = QFont(self.parent.font_family, 16)  # 预览用较小字号
        self.font_preview.setFont(preview_font)

class SubtitleConfigDialog(QDialog):
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('插入ASS语句配置')
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
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

class ConvertWorker(QRunnable):
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
                # 对于非ASS文件，设置默认样式信息
                subs.info = {
                    'Title': 'Default Aegisub file',
                    'ScriptType': 'v4.00+',
                    'WrapStyle': '0',
                    'ScaledBorderAndShadow': 'yes',
                    'YCbCr Matrix': 'TV.601',
                    'PlayResX': '1920',
                    'PlayResY': '1080'
                }

                # 设置默认字幕样式
                subs.styles['Default'] = pysubs2.SSAStyle(
                    fontname=self.font_family,
                    fontsize=self.font_size,
                    primarycolor=self.subtitle_color,
                    outlinecolor=self.outline_color,
                    shadow=1.0
                )
            else:
                # 对于ASS文件，保留原有信息但更新分辨率
                if 'PlayResX' not in subs.info or not subs.info['PlayResX']:
                    subs.info['PlayResX'] = '1920'
                if 'PlayResY' not in subs.info or not subs.info['PlayResY']:
                    subs.info['PlayResY'] = '1080'

                # 更新或创建Default样式
                if 'Default' in subs.styles:
                    # 保留原有样式，只更新颜色
                    default_style = subs.styles['Default']
                    default_style.primarycolor = self.subtitle_color
                    default_style.outlinecolor = self.outline_color
                else:
                    # 创建新的Default样式
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

class CheckableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.NoSelection)
    
    def addCheckableItem(self, text, checked=False):
        item = QListWidgetItem(self)
        self.addItem(item)
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        self.setItemWidget(item, checkbox)
    
    def getCheckedItems(self):
        return [
            self.itemWidget(self.item(i)).text()
            for i in range(self.count())
            if isinstance(self.itemWidget(self.item(i)), QCheckBox) and 
               self.itemWidget(self.item(i)).isChecked()
        ]

class SrtToAssConverter(MSFluentWindow):
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
        self.load_settings()  # 在UI初始化后加载设置
        self.init_tray()

    def initUI(self):
        """初始化现代化用户界面"""
        self.setWindowTitle('字幕格式转换器')
        self.setMinimumSize(900, 700)
        self.resize(1100, 800)

        # 设置窗口图标（如果存在）
        try:
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
            else:
                icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except:
            pass

        # 创建主界面
        self.main_interface = MainInterface(self)
        self.addSubInterface(self.main_interface, FIF.HOME, '主页')

        # 创建设置界面
        self.settings_interface = SettingsInterface(self)
        self.addSubInterface(self.settings_interface, FIF.SETTING, '设置')

        # 设置默认界面
        self.stackedWidget.setCurrentWidget(self.main_interface)

        # 连接信号
        self.main_interface.subtitle_configs = self.subtitle_configs
        self.main_interface.subtitle_color = self.subtitle_color
        self.main_interface.outline_color = self.outline_color
        self.main_interface.delete_original_after_convert = self.delete_original_after_convert
        self.main_interface.convert_to_china = self.convert_to_china

        # 连接转换信号
        self.main_interface.convert_requested.connect(self.start_conversion)
        self.settings_interface.config_changed.connect(self.on_config_changed)

        # 连接页面切换信号，用于更新设置界面显示
        self.stackedWidget.currentChanged.connect(self.on_page_changed)

        # 初始化配置列表
        self.main_interface.refresh_config_list()
        self.settings_interface.update_color_buttons()

    def on_page_changed(self, index):
        """页面切换时的处理"""
        current_widget = self.stackedWidget.widget(index)
        if current_widget == self.settings_interface:
            # 切换到设置页面时，更新所有显示
            self.settings_interface.update_output_dir_display()
            self.settings_interface.update_font_display()

    def start_conversion(self, files, insert_options, subtitle_color, outline_color, delete_original, convert_to_china):
        """开始转换处理"""
        try:
            print(f"开始转换，文件数量: {len(files)}")
            print(f"输出目录: {self.main_interface.output_directory}")

            # 检查输出目录设置
            if not self.main_interface.output_directory:
                # 没有设置输出目录，询问用户
                output_dir = QFileDialog.getExistingDirectory(
                    self,
                    "选择输出目录",
                    os.path.expanduser("~")
                )
                if not output_dir:
                    # 用户取消了选择
                    InfoBar.warning(
                        title="转换取消", content="未选择输出目录，转换已取消",
                        orient=Qt.Horizontal, isClosable=True,
                        position=InfoBarPosition.TOP, duration=3000, parent=self.main_interface
                    )
                    return

                # 保存用户选择的目录
                self.main_interface.output_directory = output_dir
                self.save_settings()

                # 更新设置界面显示
                if hasattr(self, 'settings_interface'):
                    self.settings_interface.update_output_dir_display()

                InfoBar.success(
                    title="目录已设置", content=f"输出目录已设置为: {output_dir}",
                    orient=Qt.Horizontal, isClosable=True,
                    position=InfoBarPosition.TOP, duration=3000, parent=self.main_interface
                )

            self.total_conversions = len(files)
            self.conversion_count = 0

            # 记录输出信息
            self.main_interface.output_directory_used = self.main_interface.output_directory
            self.main_interface.output_files = []

            for file_path in files:
                # 使用统一的输出目录
                filename = os.path.splitext(os.path.basename(file_path))[0] + '.ass'
                ass_file = os.path.join(self.main_interface.output_directory, filename)

                # 记录输出文件
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
            InfoBar.success(
                title="开始转换", content=f"正在转换 {len(files)} 个文件...",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self.main_interface
            )

        except Exception as e:
            print(f"转换启动失败: {e}")
            import traceback
            traceback.print_exc()
            InfoBar.error(
                title="转换失败", content=f"转换启动失败: {str(e)}",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=5000, parent=self.main_interface
            )

    def on_conversion_finished(self, _):
        """转换完成处理"""
        self.conversion_count += 1

        if self.conversion_count == self.total_conversions:
            # 所有文件转换完成
            self.main_interface.convert_button.setEnabled(True)
            self.main_interface.convert_button.setText("开始转换")

            # 显示转换完成消息
            content = f"所有文件已转换完成！保存在: {self.main_interface.output_directory_used}"

            InfoBar.success(
                title="转换完成", content=content,
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=5000, parent=self.main_interface
            )

            # 清空文件列表
            self.main_interface.clear_all_files()

            # 显示输出位置信息
            self.show_output_location_info()

    def show_output_location_info(self):
        """显示输出位置信息"""
        try:
            # 创建信息对话框
            msg_box = QMessageBox(self.main_interface)
            msg_box.setWindowTitle("转换完成")

            output_dir = self.main_interface.output_directory_used
            msg_box.setText(f"所有文件已保存到:\n{output_dir}")
            msg_box.setInformativeText("选择要执行的操作：")

            # 自定义按钮
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
            msg_box = QMessageBox(self.main_interface)
            msg_box.setWindowTitle("转换结果文件列表")
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

        InfoBar.error(
            title="转换错误", content=f"转换失败: {error_msg}",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=5000, parent=self.main_interface
        )

        if self.conversion_count == self.total_conversions:
            self.main_interface.convert_button.setEnabled(True)
            self.main_interface.convert_button.setText("开始转换")

    def on_config_changed(self):
        """配置改变处理"""
        self.main_interface.subtitle_color = self.subtitle_color
        self.main_interface.outline_color = self.outline_color

    def init_tray(self):
        """初始化系统托盘"""
        # 获取图标路径
        if hasattr(sys, '_MEIPASS'):
            application_path = sys._MEIPASS
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(application_path, 'icon.ico')

        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icon_path))

        # 创建托盘菜单
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
        config = {
            'subtitle_configs': self.subtitle_configs,
            'subtitle_color': self.subtitle_color,
            'outline_color': self.outline_color
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def load_settings(self):
        """加载程序设置"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.main_interface.output_directory = settings.get('output_directory', '')
                    self.font_family = settings.get('font_family', '方正粗圆_GBK')
                    self.font_size = settings.get('font_size', 70)
                    print(f"加载字体设置: {self.font_family}, {self.font_size}pt")
            else:
                # 设置默认值
                self.font_family = '方正粗圆_GBK'
                self.font_size = 70
                print(f"使用默认字体设置: {self.font_family}, {self.font_size}pt")
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

    def choose_color(self, color_type):
        """选择颜色"""
        color = QColorDialog.getColor()
        if color.isValid():
            color_value = f"{color.blue():02x}{color.green():02x}{color.red():02x}"
            if color_type == 'subtitle':
                self.subtitle_color = f'H00{color_value.upper()}'
            else:
                self.outline_color = f'H00{color_value.upper()}'
            self.save_subtitle_configs()
            self.update_color_buttons()

    def update_color_buttons(self):
        """更新颜色按钮显示"""
        subtitle_color = f'#{self.subtitle_color[3:5]}{self.subtitle_color[5:7]}{self.subtitle_color[7:9]}'
        outline_color = f'#{self.outline_color[3:5]}{self.outline_color[5:7]}{self.outline_color[7:9]}'
        self.subtitle_color_button.setStyleSheet(f'background-color: {subtitle_color}')
        self.outline_color_button.setStyleSheet(f'background-color: {outline_color}')





if __name__ == '__main__':
    try:
        # 设置环境变量，减少警告信息
        os.environ['QFLUENTWIDGETS_NO_TIPS'] = 'True'
        os.environ['QT_LOGGING_RULES'] = 'qt.qpa.fonts.warning=false'

        # macOS 特定优化
        if sys.platform == "darwin":
            os.environ['QT_MAC_WANTS_LAYER'] = '1'
            os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
            # 禁用输入法相关警告
            os.environ['QT_IM_MODULE'] = ''

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        # macOS 特定设置
        if sys.platform == "darwin":
            app.setAttribute(Qt.AA_DontShowIconsInMenus, True)
            app.setAttribute(Qt.AA_NativeWindows, False)

        # 设置应用程序属性
        app.setApplicationName("SRT转ASS字幕转换器")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("SubtitleConverter")

        # 设置默认字体，避免字体警告
        font = QFont()
        if sys.platform == "darwin":  # macOS
            font.setFamily("PingFang SC")
        elif sys.platform == "win32":  # Windows
            font.setFamily("Microsoft YaHei")
        else:  # Linux
            font.setFamily("Noto Sans CJK SC")
        font.setPointSize(10)
        app.setFont(font)

        # 加载中文翻译
        translator = QTranslator()
        if hasattr(QLibraryInfo, 'path'):  # Qt6
            translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
        else:  # Qt5
            translations_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)

        if translator.load('qt_zh_CN.qm', translations_path):
            app.installTranslator(translator)

        # 设置深色主题
        setTheme(Theme.DARK)

        # 创建启动画面（可选）
        splash = None
        try:
            # 创建简单的启动提示
            splash_widget = QWidget()
            splash_widget.setWindowFlags(Qt.SplashScreen | Qt.WindowStaysOnTopHint)
            splash_widget.setFixedSize(400, 200)
            splash_widget.setStyleSheet("""
                QWidget {
                    background-color: #2d2d30;
                    border-radius: 10px;
                    color: white;
                }
            """)

            splash_layout = QVBoxLayout(splash_widget)
            splash_layout.setAlignment(Qt.AlignCenter)

            title_label = QLabel("SRT 转 ASS 字幕转换器")
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 20px;")

            loading_label = QLabel("正在启动...")
            loading_label.setAlignment(Qt.AlignCenter)
            loading_label.setStyleSheet("font-size: 12px; color: #cccccc;")

            splash_layout.addWidget(title_label)
            splash_layout.addWidget(loading_label)

            # 居中显示
            screen = app.primaryScreen().geometry()
            splash_widget.move(
                (screen.width() - splash_widget.width()) // 2,
                (screen.height() - splash_widget.height()) // 2
            )

            splash_widget.show()
            app.processEvents()

            # 短暂延迟
            import time
            time.sleep(0.5)

        except Exception:
            pass  # 如果启动画面失败，继续正常启动

        # 创建并显示主窗口
        window = SrtToAssConverter()
        window.show()

        # 隐藏启动画面
        if splash_widget:
            splash_widget.hide()

        # 启动应用程序
        sys.exit(app.exec_())

    except Exception as e:
        print(f'程序启动错误: {str(e)}')
        import traceback
        traceback.print_exc()
