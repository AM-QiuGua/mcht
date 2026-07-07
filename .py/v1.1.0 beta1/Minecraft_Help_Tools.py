import sys
import json
import os
import configparser
from collections import deque
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QPushButton, QGroupBox, QFormLayout, QMessageBox,
    QSplitter, QFrame, QSizePolicy, QStatusBar, QMenuBar, QMenu,
    QToolBar, QDialog, QTabWidget, QCheckBox, QSpinBox, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QColor, QPalette, QAction
from pypinyin import lazy_pinyin

# ----- 常量 -----
JSON_FILE = "data.json"
CONFIG_FILE = "data.ini"

VERSION_LIST = ["全部", "1.0", "1.8", "1.12", "1.14", "1.16", "1.17", "1.18", "1.19", "1.20", "1.21"]
TYPE_MAP = {
    "全部": "all",
    "服务器指令": "commands",
    "物品ID": "items",
    "方块ID": "blocks",
    "药水效果": "effects",
    "附魔ID": "enchantments"
}
TARGET_PRESETS = [
    ("自定义玩家名", "custom"),
    ("@p 最近玩家", "@p"),
    ("@a 全部玩家", "@a"),
    ("@s 自己", "@s"),
    ("@e 所有实体", "@e"),
    ("@r 随机玩家", "@r")
]
ENCHANT_TARGETS = [
    ("玩家手持物品", "player_hand"),
    ("所有实体手持", "@e"),
    ("盔甲架装备", "armor_stand")
]
MAX_HISTORY = 100

# ----- 设置对话框 -----
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 设置")
        self.resize(600, 450)
        self.parent = parent

        layout = QVBoxLayout(self)

        # 选项卡
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # --- 外观 ---
        appearance_tab = QWidget()
        app_layout = QVBoxLayout(appearance_tab)
        self.dark_mode_check = QCheckBox("启用深色模式")
        self.dark_mode_check.setChecked(parent.dark_mode)
        app_layout.addWidget(self.dark_mode_check)
        app_layout.addStretch()
        tabs.addTab(appearance_tab, "外观")

        # --- 历史记录 ---
        history_tab = QWidget()
        hist_layout = QVBoxLayout(history_tab)
        hist_label = QLabel("指令历史记录 (最多100条)")
        hist_layout.addWidget(hist_label)
        self.history_list = QListWidget()
        self.load_history()
        hist_layout.addWidget(self.history_list)
        clear_hist_btn = QPushButton("清空历史记录")
        clear_hist_btn.clicked.connect(self.clear_history)
        hist_layout.addWidget(clear_hist_btn)
        tabs.addTab(history_tab, "历史记录")

        # --- 收藏夹 ---
        fav_tab = QWidget()
        fav_layout = QVBoxLayout(fav_tab)
        fav_label = QLabel("已收藏的条目 (点击可取消收藏)")
        fav_layout.addWidget(fav_label)
        self.fav_list = QListWidget()
        self.load_favorites()
        self.fav_list.itemDoubleClicked.connect(self.remove_favorite)
        fav_layout.addWidget(self.fav_list)
        tabs.addTab(fav_tab, "收藏夹")

        # --- 默认参数 ---
        param_tab = QWidget()
        param_layout = QFormLayout(param_tab)
        self.default_target = QComboBox()
        for name, val in TARGET_PRESETS:
            self.default_target.addItem(name, val)
        # 设置当前值
        idx = self.default_target.findData(parent.target_combo.currentData())
        if idx >= 0:
            self.default_target.setCurrentIndex(idx)
        param_layout.addRow("默认目标选择器：", self.default_target)

        self.default_player = QLineEdit(parent.player_input.text())
        param_layout.addRow("默认自定义玩家名：", self.default_player)

        self.default_level = QLineEdit(parent.level_input.text())
        param_layout.addRow("默认数量/等级：", self.default_level)

        self.default_duration = QLineEdit(parent.duration_input.text())
        param_layout.addRow("默认时长(秒)：", self.default_duration)

        self.default_enchant = QComboBox()
        for name, val in ENCHANT_TARGETS:
            self.default_enchant.addItem(name, val)
        idx_e = self.default_enchant.findData(parent.enchant_combo.currentData())
        if idx_e >= 0:
            self.default_enchant.setCurrentIndex(idx_e)
        param_layout.addRow("默认附魔目标：", self.default_enchant)

        tabs.addTab(param_tab, "默认参数")

        # 按钮
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def load_history(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding="utf-8")
        if config.has_section("History"):
            history = config.get("History", "commands", fallback="")
            items = history.split("||") if history else []
            for cmd in items:
                if cmd.strip():
                    self.history_list.addItem(cmd.strip())
        else:
            # 尝试从 parent 加载
            if hasattr(self.parent, 'history') and self.parent.history:
                for cmd in self.parent.history:
                    self.history_list.addItem(cmd)

    def clear_history(self):
        self.history_list.clear()
        # 同时清除 parent 的历史
        if hasattr(self.parent, 'history'):
            self.parent.history.clear()
        self.save_history()

    def save_history(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding="utf-8")
        if not config.has_section("History"):
            config.add_section("History")
        # 从列表获取
        items = [self.history_list.item(i).text() for i in range(self.history_list.count())]
        config.set("History", "commands", "||".join(items))
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            config.write(f)

    def load_favorites(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding="utf-8")
        if config.has_section("Favorites"):
            favs = config.get("Favorites", "items", fallback="")
            if favs:
                for entry_str in favs.split("||"):
                    if entry_str.strip():
                        self.fav_list.addItem(entry_str.strip())

    def remove_favorite(self, item):
        # 双击取消收藏
        name_type = item.text()
        # 从列表移除
        self.fav_list.takeItem(self.fav_list.row(item))
        # 从 parent 取消收藏
        if hasattr(self.parent, 'toggle_star'):
            # 找到对应的条目并取消星标
            for entry in self.parent.all_data:
                if f"{entry['name']} ({entry['_type']})" == name_type:
                    entry['_starred'] = False
                    break
        self.save_favorites()

    def save_favorites(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding="utf-8")
        if not config.has_section("Favorites"):
            config.add_section("Favorites")
        items = [self.fav_list.item(i).text() for i in range(self.fav_list.count())]
        config.set("Favorites", "items", "||".join(items))
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            config.write(f)

    def accept(self):
        # 应用设置
        self.parent.dark_mode = self.dark_mode_check.isChecked()
        self.parent.apply_style()

        # 默认参数
        self.parent.target_combo.setCurrentIndex(self.default_target.currentIndex())
        self.parent.player_input.setText(self.default_player.text())
        self.parent.level_input.setText(self.default_level.text())
        self.parent.duration_input.setText(self.default_duration.text())
        self.parent.enchant_combo.setCurrentIndex(self.default_enchant.currentIndex())

        # 保存所有
        self.save_history()
        self.save_favorites()
        self.parent.save_config()
        super().accept()

# ----- 主窗口 -----
class MCToolWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎮 MC 指令 & ID 全能工具箱")
        self.resize(1080, 720)
        self.setMinimumSize(920, 600)

        # 数据
        self.all_data = []
        self.current_entry = None
        self.history = deque(maxlen=MAX_HISTORY)
        self.dark_mode = False

        self.load_json()
        self._apply_style()
        self._build_ui()
        self.load_config()
        self.load_history()
        self.load_favorites()

        # 搜索防抖定时器
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.do_refresh_list)

        # 刷新列表
        self.refresh_list()

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪", 2000)

    # ────────────── 数据加载 ──────────────
    def load_json(self):
        if not os.path.exists(JSON_FILE):
            QMessageBox.critical(self, "文件缺失",
                                 f"未找到 {JSON_FILE}\n请将配置文件放到程序同目录下。")
            sys.exit(1)
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for cate_key in ["commands", "items", "blocks", "effects", "enchantments"]:
                for item in raw.get(cate_key, []):
                    item["_type"] = cate_key
                    # 预处理拼音
                    name_pinyin = ''.join(lazy_pinyin(item.get("name", "")))
                    desc_pinyin = ''.join(lazy_pinyin(item.get("desc", "")))
                    core = item.get("cmd", item.get("id", ""))
                    core_pinyin = ''.join(lazy_pinyin(core))
                    item["_pinyin"] = (name_pinyin + desc_pinyin + core_pinyin).lower()
                    item["_starred"] = False  # 将在加载收藏时标记
                    self.all_data.append(item)
        except Exception as e:
            QMessageBox.critical(self, "JSON 解析失败", f"错误信息：{str(e)}")
            sys.exit(1)

    # ────────────── 配置持久化 ──────────────
    def load_config(self):
        config = configparser.ConfigParser()
        if not os.path.exists(CONFIG_FILE):
            config["DEFAULT"] = {
                "search": "",
                "type": "全部",
                "version": "全部",
                "target": "custom",
                "player_name": "AM_QiuGua",
                "level": "1",
                "duration": "600",
                "enchant_target": "player_hand",
                "dark_mode": "false"
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                config.write(f)
        else:
            config.read(CONFIG_FILE, encoding="utf-8")

        self.search_input.setText(config.get("DEFAULT", "search", fallback=""))
        self.type_combo.setCurrentText(config.get("DEFAULT", "type", fallback="全部"))
        self.version_combo.setCurrentText(config.get("DEFAULT", "version", fallback="全部"))
        target_val = config.get("DEFAULT", "target", fallback="custom")
        for i in range(self.target_combo.count()):
            if self.target_combo.itemData(i) == target_val:
                self.target_combo.setCurrentIndex(i)
                break
        self.player_input.setText(config.get("DEFAULT", "player_name", fallback="AM_QiuGua"))
        self.level_input.setText(config.get("DEFAULT", "level", fallback="1"))
        self.duration_input.setText(config.get("DEFAULT", "duration", fallback="600"))
        enchant_val = config.get("DEFAULT", "enchant_target", fallback="player_hand")
        for i in range(self.enchant_combo.count()):
            if self.enchant_combo.itemData(i) == enchant_val:
                self.enchant_combo.setCurrentIndex(i)
                break
        self.dark_mode = config.getboolean("DEFAULT", "dark_mode", fallback=False)

    def save_config(self):
        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "search": self.search_input.text(),
            "type": self.type_combo.currentText(),
            "version": self.version_combo.currentText(),
            "target": self.target_combo.currentData(),
            "player_name": self.player_input.text(),
            "level": self.level_input.text(),
            "duration": self.duration_input.text(),
            "enchant_target": self.enchant_combo.currentData(),
            "dark_mode": str(self.dark_mode).lower()
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            config.write(f)

    def load_history(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding="utf-8")
        if config.has_section("History"):
            hist_str = config.get("History", "commands", fallback="")
            if hist_str:
                for cmd in hist_str.split("||"):
                    if cmd.strip():
                        self.history.append(cmd.strip())

    def load_favorites(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding="utf-8")
        if config.has_section("Favorites"):
            fav_str = config.get("Favorites", "items", fallback="")
            if fav_str:
                fav_list = fav_str.split("||")
                for entry in self.all_data:
                    label = f"{entry['name']} ({entry['_type']})"
                    if label in fav_list:
                        entry["_starred"] = True

    def closeEvent(self, event):
        self.save_config()
        # 保存历史
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding="utf-8")
        if not config.has_section("History"):
            config.add_section("History")
        config.set("History", "commands", "||".join(self.history))
        # 保存收藏
        if not config.has_section("Favorites"):
            config.add_section("Favorites")
        fav_list = [f"{e['name']} ({e['_type']})" for e in self.all_data if e.get("_starred", False)]
        config.set("Favorites", "items", "||".join(fav_list))
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            config.write(f)
        event.accept()

    # ────────────── 样式 ──────────────
    def apply_style(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget { background: #2b2b2b; color: #e0e0e0; }
                QGroupBox {
                    background: #3c3c3c; border: 1px solid #555; color: #eee;
                }
                QLineEdit, QComboBox, QTextEdit, QTreeWidget {
                    background: #3c3c3c; color: #eee; border: 1px solid #555;
                }
                QLineEdit:focus, QComboBox:focus { border: 1px solid #409eff; }
                QPushButton {
                    background: #4a4a4a; color: #eee; border: 1px solid #555;
                }
                QPushButton:hover { background: #5a5a5a; }
                QPushButton#primaryBtn { background: #409eff; color: white; }
                QPushButton#successBtn { background: #67c23a; color: white; }
                QTreeWidget::item:selected { background: #409eff; }
                QTreeWidget::item:hover { background: #4a4a4a; }
                QLabel#codeLabel { background: #1e1e1e; color: #4ec9b0; }
                QLabel#previewLabel { background: #1e1e1e; color: #fdcb6e; }
                QLabel { color: #e0e0e0; }
                QSplitter::handle { background: #555; }
                QStatusBar { background: #3c3c3c; color: #ddd; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background: #f0f2f5; }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #dcdfe6;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 8px;
                    background: #ffffff;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 6px;
                    color: #303133;
                }
                QLineEdit, QComboBox {
                    padding: 5px 8px;
                    border: 1px solid #dcdfe6;
                    border-radius: 4px;
                    background: #ffffff;
                    selection-background-color: #409eff;
                }
                QLineEdit:focus, QComboBox:focus {
                    border: 1px solid #409eff;
                }
                QPushButton {
                    padding: 7px 16px;
                    border-radius: 4px;
                    background: #ffffff;
                    border: 1px solid #dcdfe6;
                    color: #303133;
                }
                QPushButton:hover {
                    background: #ecf5ff;
                    border: 1px solid #b3d8ff;
                    color: #409eff;
                }
                QPushButton#primaryBtn {
                    background: #409eff;
                    color: white;
                    border: 1px solid #409eff;
                    font-weight: bold;
                    padding: 9px 20px;
                }
                QPushButton#primaryBtn:hover {
                    background: #66b1ff;
                    border: 1px solid #66b1ff;
                }
                QPushButton#successBtn {
                    background: #67c23a;
                    color: white;
                    border: 1px solid #67c23a;
                    padding: 8px 16px;
                }
                QPushButton#successBtn:hover {
                    background: #85ce61;
                    border: 1px solid #85ce61;
                }
                QTreeWidget {
                    border: 1px solid #dcdfe6;
                    border-radius: 6px;
                    background: #ffffff;
                    outline: none;
                }
                QTreeWidget::item {
                    padding: 4px 6px;
                    border-bottom: 1px solid #f5f7fa;
                }
                QTreeWidget::item:selected {
                    background: #ecf5ff;
                    color: #409eff;
                }
                QTreeWidget::item:hover {
                    background: #f5f7fa;
                }
                QTextEdit {
                    border: 1px solid #dcdfe6;
                    border-radius: 6px;
                    background: #fafafa;
                    padding: 8px;
                    font-family: "Microsoft YaHei";
                }
                QLabel#codeLabel {
                    background: #1e1e1e;
                    color: #4ec9b0;
                    font-family: "Consolas", "Courier New";
                    font-size: 13px;
                    padding: 10px 14px;
                    border-radius: 6px;
                }
                QLabel#previewLabel {
                    background: #2d3436;
                    color: #fdcb6e;
                    font-family: "Consolas", "Courier New";
                    font-size: 12px;
                    padding: 8px 12px;
                    border-radius: 4px;
                }
                QLabel#titleLabel {
                    font-size: 15px;
                    font-weight: bold;
                    color: #303133;
                }
                QLabel#countLabel {
                    color: #909399;
                    font-size: 12px;
                }
                QSplitter::handle {
                    background: #e4e7ed;
                    width: 2px;
                }
            """)

    def _apply_style(self):
        self.apply_style()

    # ────────────── 界面构建 ──────────────
    def _build_ui(self):
        # 菜单栏
        menubar = self.menuBar()
        settings_menu = QMenu("设置", self)
        settings_action = QAction("打开设置", self)
        settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(settings_action)
        menubar.addMenu(settings_menu)

        # 工具栏（收藏按钮）
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        self.star_action = QAction("⭐ 收藏", self)
        self.star_action.setCheckable(True)
        self.star_action.triggered.connect(self.toggle_star)
        toolbar.addAction(self.star_action)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ── 顶部筛选栏 ──
        filter_group = QGroupBox("🔍 筛选条件")
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)

        filter_layout.addWidget(QLabel("关键词："))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入名称/ID/说明/拼音...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        filter_layout.addWidget(self.search_input, stretch=2)

        filter_layout.addWidget(QLabel("类型："))
        self.type_combo = QComboBox()
        self.type_combo.addItems(list(TYPE_MAP.keys()))
        self.type_combo.currentTextChanged.connect(self.refresh_list)
        filter_layout.addWidget(self.type_combo)

        filter_layout.addWidget(QLabel("最高版本："))
        self.version_combo = QComboBox()
        self.version_combo.addItems(VERSION_LIST)
        self.version_combo.currentTextChanged.connect(self.refresh_list)
        filter_layout.addWidget(self.version_combo)

        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        # ── 主体分割区 ──
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_label = QLabel("📋 结果列表")
        title_label.setObjectName("titleLabel")
        title_row.addWidget(title_label)
        title_row.addStretch()
        self.count_label = QLabel("共 0 条结果")
        self.count_label.setObjectName("countLabel")
        title_row.addWidget(self.count_label)
        left_layout.addLayout(title_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "版本", "类型"])
        self.tree.setColumnWidth(0, 260)
        self.tree.setColumnWidth(1, 60)
        self.tree.setColumnWidth(2, 80)
        self.tree.currentItemChanged.connect(self.on_select)
        left_layout.addWidget(self.tree)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        detail_label = QLabel("📖 详情说明")
        detail_label.setObjectName("titleLabel")
        right_layout.addWidget(detail_label)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        self.info_text.setText("← 请在左侧列表选择一项查看详情")
        right_layout.addWidget(self.info_text)

        core_label = QLabel("💻 核心内容 (ID / 指令)")
        core_label.setObjectName("titleLabel")
        right_layout.addWidget(core_label)

        self.code_label = QLabel("（未选中）")
        self.code_label.setObjectName("codeLabel")
        self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        right_layout.addWidget(self.code_label)

        # 参数面板
        param_group = QGroupBox("⚙️ 指令参数拼接")
        param_layout = QFormLayout()
        param_layout.setSpacing(6)

        self.target_combo = QComboBox()
        for name, val in TARGET_PRESETS:
            self.target_combo.addItem(name, val)
        self.target_combo.currentIndexChanged.connect(self.update_preview)
        param_layout.addRow("目标选择器：", self.target_combo)

        self.player_input = QLineEdit()
        self.player_input.setText("AM_QiuGua")
        self.player_input.textChanged.connect(self.update_preview)
        param_layout.addRow("自定义玩家名：", self.player_input)

        self.level_input = QLineEdit()
        self.level_input.setText("1")
        self.level_input.textChanged.connect(self.update_preview)
        param_layout.addRow("数量 / 等级：", self.level_input)

        self.duration_input = QLineEdit()
        self.duration_input.setText("600")
        self.duration_input.textChanged.connect(self.update_preview)
        param_layout.addRow("时长 (秒)：", self.duration_input)

        self.enchant_combo = QComboBox()
        for name, val in ENCHANT_TARGETS:
            self.enchant_combo.addItem(name, val)
        self.enchant_combo.currentIndexChanged.connect(self.update_preview)
        param_layout.addRow("附魔目标：", self.enchant_combo)

        param_group.setLayout(param_layout)
        right_layout.addWidget(param_group)

        preview_label = QLabel("👁️ 指令预览")
        preview_label.setObjectName("titleLabel")
        right_layout.addWidget(preview_label)

        self.preview_label = QLabel("（选择条目后自动生成）")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.preview_label.setWordWrap(True)
        right_layout.addWidget(self.preview_label)

        right_layout.addStretch()

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        tip_label = QLabel("💡 修改参数后预览自动更新")
        tip_label.setStyleSheet("color: #909399; font-size: 12px;")
        btn_row.addWidget(tip_label)
        btn_row.addStretch()

        copy_core_btn = QPushButton("📋 复制核心内容")
        copy_core_btn.setObjectName("successBtn")
        copy_core_btn.clicked.connect(self.copy_core)
        btn_row.addWidget(copy_core_btn)

        copy_full_btn = QPushButton("🚀 复制完整指令")
        copy_full_btn.setObjectName("primaryBtn")
        copy_full_btn.clicked.connect(self.copy_full)
        btn_row.addWidget(copy_full_btn)

        right_layout.addLayout(btn_row)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([520, 460])

        main_layout.addWidget(splitter, stretch=1)

    # ────────────── 搜索防抖 ──────────────
    def on_search_text_changed(self):
        self.search_timer.start(200)

    # ────────────── 列表刷新（含拼音、收藏置顶） ──────────────
    def refresh_list(self):
        self.search_timer.stop()
        self.do_refresh_list()

    def do_refresh_list(self):
        keyword = self.search_input.text().strip().lower()
        type_filter = TYPE_MAP[self.type_combo.currentText()]
        ver_filter = self.version_combo.currentText()

        self.tree.clear()
        filtered = []

        for entry in self.all_data:
            # 类型
            if type_filter != "all" and entry["_type"] != type_filter:
                continue
            # 版本
            if ver_filter != "全部":
                try:
                    entry_ver_str = entry.get("version", "1.0").split('.')[:2]
                    entry_ver = float(".".join(entry_ver_str))
                    max_ver = float(ver_filter)
                    if entry_ver > max_ver:
                        continue
                except (ValueError, TypeError):
                    pass
            # 关键词匹配（含拼音）
            if keyword:
                name = entry.get("name", "").lower()
                core = entry.get("cmd", entry.get("id", "")).lower()
                desc = entry.get("desc", "").lower()
                pinyin = entry.get("_pinyin", "")
                if keyword not in name and keyword not in core and keyword not in desc and keyword not in pinyin:
                    continue
            filtered.append(entry)

        # 排序：收藏置顶
        filtered.sort(key=lambda e: (not e.get("_starred", False), e.get("name", "")))

        for entry in filtered:
            type_cn = self._type_cn(entry["_type"])
            star_mark = "⭐ " if entry.get("_starred", False) else "   "
            item = QTreeWidgetItem([
                f"{star_mark}{entry['name']}",
                entry.get("version", "1.0"),
                type_cn
            ])
            item.setData(0, Qt.UserRole, entry)
            self.tree.addTopLevelItem(item)

        self.count_label.setText(f"共 {len(filtered)} 条结果")
        self.current_entry = None
        # 清除预览
        self.preview_label.setText("（选择条目后自动生成）")

    def _type_cn(self, key):
        for cn, en in TYPE_MAP.items():
            if en == key:
                return cn
        return "未知"

    # ────────────── 收藏功能 ──────────────
    def toggle_star(self):
        if not self.current_entry:
            self.status_bar.showMessage("⚠️ 请先选择要收藏的条目", 2000)
            self.star_action.setChecked(False)
            return
        # 切换星标
        current = self.current_entry
        current["_starred"] = not current.get("_starred", False)
        self.star_action.setChecked(current["_starred"])
        self.status_bar.showMessage(f"{'⭐ 已收藏' if current['_starred'] else '☆ 已取消收藏'}: {current['name']}", 2000)
        self.refresh_list()  # 刷新列表重新排序

    def on_select(self, current, previous):
        if not current:
            self.current_entry = None
            self.star_action.setChecked(False)
            self.update_param_visibility(None)
            return
        entry = current.data(0, Qt.UserRole)
        if not entry:
            return
        self.current_entry = entry
        self.star_action.setChecked(entry.get("_starred", False))

        core_key = "cmd" if "cmd" in entry else "id"
        core_val = entry[core_key]

        info = (
            f"【名称】{entry['name']}\n"
            f"【类型】{self._type_cn(entry['_type'])}\n"
            f"【加入版本】{entry.get('version', '1.0')}\n\n"
            f"【说明】\n{entry.get('desc', '暂无说明')}"
        )
        self.info_text.setText(info)
        self.code_label.setText(core_val)

        self.update_param_visibility(entry)
        self.update_preview()

    # ────────────── 参数联动 ──────────────
    def update_param_visibility(self, entry):
        if not entry:
            self.level_input.setEnabled(False)
            self.duration_input.setEnabled(False)
            self.enchant_combo.setEnabled(False)
            return

        etype = entry["_type"]
        if etype == "commands":
            self.level_input.setEnabled(False)
            self.duration_input.setEnabled(False)
            self.enchant_combo.setEnabled(False)
        elif etype in ("items", "blocks"):
            self.level_input.setEnabled(True)
            self.duration_input.setEnabled(False)
            self.enchant_combo.setEnabled(False)
        elif etype == "effects":
            self.level_input.setEnabled(True)
            self.duration_input.setEnabled(True)
            self.enchant_combo.setEnabled(False)
        elif etype == "enchantments":
            self.level_input.setEnabled(True)
            self.duration_input.setEnabled(False)
            self.enchant_combo.setEnabled(True)
        else:
            self.level_input.setEnabled(True)
            self.duration_input.setEnabled(True)
            self.enchant_combo.setEnabled(True)

    # ────────────── 预览生成 ──────────────
    def _get_target(self):
        target_val = self.target_combo.currentData()
        if target_val == "custom":
            return self.player_input.text().strip() or "AM_QiuGua"
        return target_val

    def update_preview(self):
        if not self.current_entry:
            self.preview_label.setText("（选择条目后自动生成）")
            return

        etype = self.current_entry["_type"]
        target = self._get_target()
        level = self.level_input.text().strip() or "1"
        duration = self.duration_input.text().strip() or "600"
        core = self.current_entry.get("cmd", self.current_entry.get("id", ""))

        if etype == "commands":
            cmd = core
            if "AM_QiuGua" in cmd:
                cmd = cmd.replace("AM_QiuGua", target)
            full_cmd = cmd
        elif etype in ("items", "blocks"):
            full_cmd = f"give {target} {core} {level}"
        elif etype == "effects":
            full_cmd = f"effect give {target} {core} {duration} {level}"
        elif etype == "enchantments":
            enchant_target = self.enchant_combo.currentData()
            if enchant_target == "player_hand":
                full_cmd = f"enchant {target} {core} {level}"
            elif enchant_target == "armor_stand":
                full_cmd = f"enchant @e[type=armor_stand] {core} {level}"
            else:
                full_cmd = f"enchant {target} {core} {level}"
        else:
            full_cmd = core

        self.preview_label.setText(full_cmd)
        # 如果当前条目是 commands 且包含占位，也会生成完整指令（占位替换）
        # 保存到历史（仅当有效且不是占位提示）
        if full_cmd and "（" not in full_cmd:
            self.history.append(full_cmd)
            if len(self.history) > MAX_HISTORY:
                self.history.popleft()

    # ────────────── 复制功能 ──────────────
    def copy_core(self):
        if not self.current_entry:
            self.status_bar.showMessage("⚠️ 未选中任何条目", 2000)
            return
        core = self.current_entry.get("cmd", self.current_entry.get("id", ""))
        try:
            QApplication.clipboard().setText(core)
            self.status_bar.showMessage(f"✅ 已复制核心内容：{core[:30]}{'...' if len(core)>30 else ''}", 3000)
        except Exception as e:
            self.status_bar.showMessage(f"❌ 复制失败：{str(e)}", 3000)

    def copy_full(self):
        if not self.current_entry:
            self.status_bar.showMessage("⚠️ 未选中任何条目", 2000)
            return
        full = self.preview_label.text()
        if "（" in full and "）" in full:
            self.status_bar.showMessage("⚠️ 当前条目无法生成完整指令，请复制核心内容", 3000)
            return
        try:
            QApplication.clipboard().setText(full)
            self.status_bar.showMessage(f"✅ 完整指令已复制：{full[:40]}{'...' if len(full)>40 else ''}", 3000)
        except Exception as e:
            self.status_bar.showMessage(f"❌ 复制失败：{str(e)}", 3000)

    # ────────────── 设置窗口 ──────────────
    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

# ----- 启动 -----
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))
    window = MCToolWindow()
    window.show()
    sys.exit(app.exec())