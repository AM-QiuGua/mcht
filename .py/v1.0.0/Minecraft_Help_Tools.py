import sys
import json
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QPushButton, QGroupBox, QFormLayout, QMessageBox,
    QSplitter, QFrame, QSizePolicy  # pyright: ignore[reportUnusedImport]
)
from PySide6.QtCore import Qt, Signal  # pyright: ignore[reportUnusedImport]
from PySide6.QtGui import QFont, QIcon, QColor, QPalette  # pyright: ignore[reportUnusedImport]

JSON_FILE = "data.json"

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


class MCToolWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎮 MC 指令 & ID 全能工具箱")
        self.resize(1080, 720)
        self.setMinimumSize(920, 600)

        # 数据
        self.all_data = []  # pyright: ignore[reportUnannotatedClassAttribute]
        self.current_entry = None  # pyright: ignore[reportUnannotatedClassAttribute]
        self.load_json()

        # 样式
        self._apply_style()

        # 构建界面
        self._build_ui()

        # 刷新列表
        self.refresh_list()

    # ────────────── 数据加载 ──────────────
    def load_json(self):
        if not os.path.exists(JSON_FILE):
            QMessageBox.critical(self, "文件缺失",  # pyright: ignore[reportUnusedCallResult]
                                 f"未找到 {JSON_FILE}\n请将配置文件放到程序同目录下。")
            sys.exit(1)
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)  # pyright: ignore[reportAny]
            for cate_key in ["commands", "items", "blocks", "effects", "enchantments"]:
                for item in raw.get(cate_key, []):  # pyright: ignore[reportAny]
                    item["_type"] = cate_key
                    self.all_data.append(item)  # pyright: ignore[reportUnknownMemberType, reportAny]
        except Exception as e:
            _ = QMessageBox.critical(self, "JSON 解析失败", f"错误信息：{str(e)}")
            sys.exit(1)

    # ────────────── 样式 ──────────────
    def _apply_style(self):
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

    # ────────────── 界面构建 ──────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ── 顶部筛选栏 ──
        filter_group = QGroupBox("🔍 筛选条件")
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)

        # 搜索
        filter_layout.addWidget(QLabel("关键词："))
        self.search_input = QLineEdit()  # pyright: ignore[reportUnannotatedClassAttribute]
        self.search_input.setPlaceholderText("输入名称/ID/说明关键词...")
        _ = self.search_input.textChanged.connect(self.refresh_list)
        filter_layout.addWidget(self.search_input, stretch=2)

        # 类型
        filter_layout.addWidget(QLabel("类型："))
        self.type_combo = QComboBox()  # pyright: ignore[reportUnannotatedClassAttribute]
        self.type_combo.addItems(list(TYPE_MAP.keys()))
        _ = self.type_combo.currentTextChanged.connect(self.refresh_list)
        filter_layout.addWidget(self.type_combo)

        # 版本
        filter_layout.addWidget(QLabel("最高版本："))
        self.version_combo = QComboBox()  # pyright: ignore[reportUnannotatedClassAttribute]
        self.version_combo.addItems(VERSION_LIST)
        _ = self.version_combo.currentTextChanged.connect(self.refresh_list)
        filter_layout.addWidget(self.version_combo)

        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        # ── 主体分割区 ──
        splitter = QSplitter(Qt.Horizontal)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]

        # 左侧列表
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

        # 右侧详情
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # 详情说明
        detail_label = QLabel("📖 详情说明")
        detail_label.setObjectName("titleLabel")
        right_layout.addWidget(detail_label)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(180)
        self.info_text.setText("← 请在左侧列表选择一项查看详情")
        right_layout.addWidget(self.info_text)

        # 核心内容
        core_label = QLabel("💻 核心内容 (ID / 指令)")
        core_label.setObjectName("titleLabel")
        right_layout.addWidget(core_label)

        self.code_label = QLabel("（未选中）")
        self.code_label.setObjectName("codeLabel")
        self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownArgumentType]
        right_layout.addWidget(self.code_label)

        # 参数面板
        param_group = QGroupBox("⚙️ 指令参数拼接")
        param_layout = QFormLayout()
        param_layout.setSpacing(8)

        # 目标选择器
        self.target_combo = QComboBox()
        for name, val in TARGET_PRESETS:
            self.target_combo.addItem(name, val)
        self.target_combo.currentIndexChanged.connect(self.update_preview)
        param_layout.addRow("目标选择器：", self.target_combo)

        # 自定义玩家名
        self.player_input = QLineEdit()  # pyright: ignore[reportUnannotatedClassAttribute]
        self.player_input.setText("AM_QiuGua")
        _ = self.player_input.textChanged.connect(self.update_preview)
        param_layout.addRow("自定义玩家名：", self.player_input)

        # 数量/等级
        self.level_input = QLineEdit()
        self.level_input.setText("1")
        _ = self.level_input.textChanged.connect(self.update_preview)
        param_layout.addRow("数量 / 等级：", self.level_input)

        # 时长
        self.duration_input = QLineEdit()  # pyright: ignore[reportUnannotatedClassAttribute]
        self.duration_input.setText("600")
        _ = self.duration_input.textChanged.connect(self.update_preview)
        param_layout.addRow("时长 (秒)：", self.duration_input)

        # 附魔目标类型
        self.enchant_combo = QComboBox()
        for name, val in ENCHANT_TARGETS:
            self.enchant_combo.addItem(name, val)
        self.enchant_combo.currentIndexChanged.connect(self.update_preview)
        param_layout.addRow("附魔目标：", self.enchant_combo)

        param_group.setLayout(param_layout)
        right_layout.addWidget(param_group)

        # 预览
        preview_label = QLabel("👁️ 指令预览")
        preview_label.setObjectName("titleLabel")
        right_layout.addWidget(preview_label)

        self.preview_label = QLabel("（选择条目后自动生成）")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
        self.preview_label.setWordWrap(True)
        right_layout.addWidget(self.preview_label)

        right_layout.addStretch()

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        tip_label = QLabel("💡 修改参数后预览自动更新，复制后粘贴到服务端控制台直接使用")
        tip_label.setStyleSheet("color: #909399; font-size: 12px;")
        btn_row.addWidget(tip_label)
        btn_row.addStretch()

        copy_core_btn = QPushButton("📋 复制核心内容")
        copy_core_btn.setObjectName("successBtn")
        _ = copy_core_btn.clicked.connect(self.copy_core)
        btn_row.addWidget(copy_core_btn)

        copy_full_btn = QPushButton("🚀 复制完整指令")
        copy_full_btn.setObjectName("primaryBtn")
        _ = copy_full_btn.clicked.connect(self.copy_full)
        btn_row.addWidget(copy_full_btn)

        right_layout.addLayout(btn_row)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([520, 460])

        main_layout.addWidget(splitter, stretch=1)

    # ────────────── 列表刷新 ──────────────
    def refresh_list(self):
        keyword = self.search_input.text().strip().lower()
        type_filter = TYPE_MAP[self.type_combo.currentText()]
        ver_filter = self.version_combo.currentText()

        self.tree.clear()
        filtered = []

        for entry in self.all_data:  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            # 类型筛选
            if type_filter != "all" and entry["_type"] != type_filter:
                continue
            # 版本筛选
            if ver_filter != "全部":
                try:
                    # 截取前两段版本号(如1.20.1取1.20)进行float转换，避免多段版本号导致ValueError
                    entry_ver_str = entry.get("version", "1.0").split('.')[:2]  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
                    entry_ver = float(".".join(entry_ver_str))  # pyright: ignore[reportUnknownArgumentType]
                    max_ver = float(ver_filter)
                    if entry_ver > max_ver:
                        continue
                except (ValueError, TypeError):
                    # 如果版本号格式异常无法转换，默认予以保留，避免因数据问题导致列表为空
                    pass
            # 关键词筛选
            name = entry.get("name", "").lower()  # pyright: ignore[reportUnknownMemberType]
            core = entry.get("cmd", entry.get("id", "")).lower()  # pyright: ignore[reportUnknownMemberType]
            desc = entry.get("desc", "").lower()  # pyright: ignore[reportUnknownMemberType]
            if keyword and keyword not in name and keyword not in core and keyword not in desc:
                continue
            filtered.append(entry)

        # 填充
        for entry in filtered:
            type_cn = self._type_cn(entry["_type"])
            item = QTreeWidgetItem([  # pyright: ignore[reportUnknownArgumentType]
                f"  {entry['name']}",
                entry.get("version", "1.0"),  # pyright: ignore[reportUnknownMemberType]
                type_cn
            ])
            item.setData(0, Qt.UserRole, entry)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
            self.tree.addTopLevelItem(item)

        self.count_label.setText(f"共 {len(filtered)} 条结果")
        self.current_entry = None

    def _type_cn(self, key):
        for cn, en in TYPE_MAP.items():
            if en == key:
                return cn
        return "未知"

    # ────────────── 选中事件 ──────────────
    def on_select(self, current, previous):  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
        if not current:
            self.current_entry = None
            return
        entry = current.data(0, Qt.UserRole)  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
        if not entry:
            return
        self.current_entry = entry  # pyright: ignore[reportUnknownMemberType]

        core_key = "cmd" if "cmd" in entry else "id"
        core_val = entry[core_key]

        # 更新详情
        info = (
            f"【名称】{entry['name']}\n"
            f"【类型】{self._type_cn(entry['_type'])}\n"
            f"【加入版本】{entry.get('version', '1.0')}\n\n"
            f"【说明】\n{entry.get('desc', '暂无说明')}"
        )
        self.info_text.setText(info)

        # 更新核心内容
        self.code_label.setText(core_val)

        # 更新预览
        self.update_preview()

    # ────────────── 预览生成 ──────────────
    def _get_target(self):
        """获取目标字符串"""
        target_val = self.target_combo.currentData()  # pyright: ignore[reportAny]
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
            # 指令类：如果包含玩家占位就替换，否则直接显示
            cmd = core
            # 简单替换常见的玩家名
            if "AM_QiuGua" in cmd:
                cmd = cmd.replace("AM_QiuGua", target)
            self.preview_label.setText(cmd)

        elif etype in ("items", "blocks"):
            self.preview_label.setText(f"give {target} {core} {level}")

        elif etype == "effects":
            self.preview_label.setText(f"effect give {target} {core} {duration} {level}")

        elif etype == "enchantments":
            enchant_target = self.enchant_combo.currentData()
            if enchant_target == "player_hand":
                self.preview_label.setText(f"enchant {target} {core} {level}")
            elif enchant_target == "armor_stand":
                self.preview_label.setText(f"enchant @e[type=armor_stand] {core} {level}")
            else:
                self.preview_label.setText(f"enchant {target} {core} {level}")

    # ────────────── 复制功能 ──────────────
    def copy_core(self):
        if not self.current_entry:
            QMessageBox.warning(self, "未选中", "请先在左侧列表选择一项！")
            return
        core = self.current_entry.get("cmd", self.current_entry.get("id", ""))
        try:
            QApplication.clipboard().setText(core)
            QMessageBox.information(self, "复制成功", f"已复制到剪贴板：\n{core}")
        except Exception as e:
            QMessageBox.warning(self, "复制失败", f"无法写入剪贴板，可能被其他程序占用。\n错误信息：{str(e)}")

    def copy_full(self):
        if not self.current_entry:
            QMessageBox.warning(self, "未选中", "请先在左侧列表选择一项！")
            return
        full = self.preview_label.text()
        if "（" in full and "）" in full:
            QMessageBox.warning(self, "无法生成", "当前条目无法生成完整指令，请复制核心内容")
            return
        try:
            QApplication.clipboard().setText(full)
            QMessageBox.information(self, "复制成功",
                                    f"完整指令已复制：\n{full}\n\n直接粘贴到服务端控制台即可执行")
        except Exception as e:
            QMessageBox.warning(self, "复制失败", f"无法写入剪贴板，可能被其他程序占用。\n错误信息：{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))
    window = MCToolWindow()
    window.show()
    sys.exit(app.exec())
