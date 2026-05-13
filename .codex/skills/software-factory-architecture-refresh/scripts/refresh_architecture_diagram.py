from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import cairosvg
except Exception:  # pragma: no cover
    cairosvg = None


STATUS_ORDER = {"未完成": 2, "部分完成": 1, "已完成": 0}
OUTPUT_DIR = Path("artifacts/architecture")
SVG_NAME = "software-factory-architecture.svg"
PNG_NAME = "software-factory-architecture.png"
DATA_NAME = "software-factory-architecture.data.json"
REPORT_NAME = "software-factory-architecture-status.md"

PALETTES = {
    "done": {"fill": "#f0fdf4", "stroke": "#16a34a", "accent_fill": "#dcfce7", "line_stroke": "#86efac"},
    "partial": {"fill": "#fff7ed", "stroke": "#f59e0b", "accent_fill": "#fed7aa", "line_stroke": "#fdba74"},
    "todo": {"fill": "#fef2f2", "stroke": "#ef4444", "accent_fill": "#fecaca", "line_stroke": "#fca5a5"},
    "info": {"fill": "#eff6ff", "stroke": "#2563eb", "accent_fill": "#dbeafe", "line_stroke": "#93c5fd"},
    "boundary": {"fill": "#f5f3ff", "stroke": "#8b5cf6", "accent_fill": "#ddd6fe", "line_stroke": "#c4b5fd"},
    "storage": {"fill": "#ecfeff", "stroke": "#0891b2", "accent_fill": "#cffafe", "line_stroke": "#67e8f9"},
    "evidence": {"fill": "#f0fdfa", "stroke": "#0f766e", "accent_fill": "#ccfbf1", "line_stroke": "#5eead4"},
}

CANVAS_WIDTH = 2240
TOP_COLUMN_WIDTH = 940
TOP_COLUMN_GAP = 30
PAGE_MARGIN_X = 40
PAGE_MARGIN_TOP = 170
SECTION_GAP_Y = 28
BOTTOM_SECTION_WIDTH = 1445
BOTTOM_SECTION_GAP = 30
NODE_HEIGHT = 68
SECTION_PADDING_X = 18
SECTION_PADDING_Y = 18
SECTION_HEADER_HEIGHT = 46
GRID_GAP_X = 14
GRID_GAP_Y = 14


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_generator() -> Any:
    module_path = skill_root() / "scripts" / "fireworks_generate_from_template.py"
    spec = importlib.util.spec_from_file_location("fireworks_generate_from_template", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"Unable to load diagram generator: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_status_table(status_doc: Path) -> tuple[dict[str, str], dict[str, Counter[str]]]:
    status_by_id: dict[str, str] = {}
    counts = {"F": Counter(), "INF": Counter(), "ALL": Counter()}
    for raw_line in status_doc.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not (line.startswith("| F-") or line.startswith("| INF-")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        item_id = cells[0]
        status = cells[-2]
        if status not in STATUS_ORDER:
            continue
        status_by_id[item_id] = status
        bucket = "INF" if item_id.startswith("INF-") else "F"
        counts[bucket][status] += 1
        counts["ALL"][status] += 1
    return status_by_id, counts


def aggregate_status(status_ids: list[str], status_by_id: dict[str, str], default_status: str = "已完成") -> str:
    if not status_ids:
        return default_status
    related = [status_by_id.get(item_id) for item_id in status_ids if status_by_id.get(item_id)]
    if not related:
        return default_status
    return max(related, key=lambda value: STATUS_ORDER[value])


def palette_for_node(node: dict[str, Any], resolved_status: str) -> dict[str, str]:
    palette_id = node.get("palette")
    if palette_id:
        return PALETTES[palette_id]
    if resolved_status == "未完成":
        return PALETTES["todo"]
    if resolved_status == "部分完成":
        return PALETTES["partial"]
    return PALETTES["done"]


def normalize_tags(tags: list[str]) -> list[dict[str, str]]:
    return [{"label": tag} for tag in tags if tag]


TYPE_LABEL_ZH = {
    "AI": "智能",
    "BOOT": "引导",
    "COMP": "组件",
    "CTX": "上下文",
    "DATA": "数据",
    "DIALOG": "弹窗",
    "ENTRY": "入口",
    "FS": "存储",
    "HOOK": "钩子",
    "HTML": "页面",
    "INPUT": "输入",
    "IPC": "通道",
    "LIB": "库",
    "MODEL": "模型",
    "OWNER": "归属",
    "PAGE": "页面",
    "PLAN": "规划",
    "PLATFORM": "平台",
    "PRELOAD": "预加载",
    "PROJECT": "项目",
    "RUNTIME": "运行时",
    "RULES": "规则",
    "SCHEMA": "契约",
    "SERVICE": "服务",
    "SHARED": "共享",
    "STORE": "存储",
    "STYLE": "样式",
    "TYPE": "类型",
    "UI": "界面",
    "UTIL": "工具",
    "WORKBENCH": "工作台",
}

SECTION_HEADER_ZH = {
    "AI": "智能层",
    "DATA": "数据层",
    "EDITOR": "编辑器",
    "IPC": "进程边界",
    "PLANNED": "待建设",
    "PLATFORM": "平台层",
    "PROJECT": "工程层",
    "RECOVERY": "治理恢复",
    "RENDERER": "渲染层",
    "RUNTIME": "运行时",
    "RULES": "规则沉淀",
    "SHARED": "共享契约",
    "WORKBENCH": "工作台",
}


def localize_type_label(label: str) -> str:
    return TYPE_LABEL_ZH.get(label, label)


def localize_section_header(label: str) -> str:
    return SECTION_HEADER_ZH.get(label, label)


def resolve_node(node: dict[str, Any], status_by_id: dict[str, str], root: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    resolved_status = node.get("manual_status") or aggregate_status(node.get("status_ids", []), status_by_id)
    palette = palette_for_node(node, resolved_status)
    tags = list(node.get("tags", []))
    if node.get("show_status_tag", True) and resolved_status in STATUS_ORDER:
        tags.insert(0, resolved_status)

    owner_paths = [Path(path) for path in node.get("owner_paths", [])]
    missing_paths = [str(path).replace("\\", "/") for path in owner_paths if not (root / path).exists()]

    svg_node = {
        "id": node["id"],
        "kind": node["kind"],
        "x": node["x"],
        "y": node["y"],
        "width": node["width"],
        "height": node["height"],
        "label": node["label"],
        "sublabel": node.get("sublabel", ""),
        "type_label": localize_type_label(node.get("type_label", "")),
        "fill": palette["fill"],
        "stroke": palette["stroke"],
        "accent_fill": palette["accent_fill"],
        "line_stroke": palette["line_stroke"],
        "tags": normalize_tags(tags),
    }
    if node["kind"] == "bot":
        svg_node["body_fill"] = "#111827"
        svg_node["accent_fill"] = palette["stroke"]

    report_row = None
    if node.get("report", True):
        report_row = {
            "group": node.get("report_group", "未分组"),
            "name": node["label"],
            "status": resolved_status,
            "status_ids": node.get("status_ids", []),
            "owner_paths": [str(path).replace("\\", "/") for path in owner_paths],
            "missing_paths": missing_paths,
            "note": node.get("status_note", ""),
        }
    return svg_node, report_row


def build_report(rows: list[dict[str, Any]], output_path: Path) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["group"], []).append(row)

    lines = [
        "# Software Factory 系统设计架构状态摘要",
        "",
        "| 模块组 | 模块 | 状态 | 关联状态 ID | 关键代码 | 备注 |",
        "|---|---|---|---|---|---|",
    ]
    for group_name, group_rows in grouped.items():
        for index, row in enumerate(group_rows):
            group_cell = group_name if index == 0 else ""
            status_ids = "<br>".join(row["status_ids"]) if row["status_ids"] else "-"
            owner_paths = "<br>".join(row["owner_paths"]) if row["owner_paths"] else "-"
            notes = []
            if row["note"]:
                notes.append(row["note"])
            if row["missing_paths"]:
                notes.append(f"缺失代码路径: {', '.join(row['missing_paths'])}")
            note_cell = "<br>".join(notes) if notes else "-"
            lines.append(f"| {group_cell} | {row['name']} | {row['status']} | {status_ids} | {owner_paths} | {note_cell} |")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def node(
    node_id: str,
    label: str,
    sublabel: str,
    *,
    kind: str = "rect",
    type_label: str = "MODULE",
    status_ids: list[str] | None = None,
    owner_paths: list[str] | None = None,
    manual_status: str | None = None,
    palette: str | None = None,
    tags: list[str] | None = None,
    status_note: str = "",
    report_group: str = "",
    report: bool = True,
    show_status_tag: bool = True,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "label": label,
        "sublabel": sublabel,
        "kind": kind,
        "type_label": type_label,
        "status_ids": status_ids or [],
        "owner_paths": owner_paths or [],
        "manual_status": manual_status,
        "palette": palette,
        "tags": tags or [],
        "status_note": status_note,
        "report_group": report_group,
        "report": report,
        "show_status_tag": show_status_tag,
    }


def section_height(section: dict[str, Any]) -> int:
    cols = section.get("cols", 4)
    rows = max(1, math.ceil(len(section["nodes"]) / cols))
    return SECTION_HEADER_HEIGHT + (SECTION_PADDING_Y * 2) + (rows * NODE_HEIGHT) + ((rows - 1) * GRID_GAP_Y)


def place_section(section: dict[str, Any], x: int, y: int, width: int) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    cols = section.get("cols", 4)
    height = section_height(section)
    usable_width = width - (SECTION_PADDING_X * 2) - ((cols - 1) * GRID_GAP_X)
    node_width = usable_width // cols
    container = {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "label": section["label"],
        "header_prefix": section["header_prefix"],
        "header_text": localize_section_header(section["header_text"]),
    }
    placed_nodes: list[dict[str, Any]] = []
    for index, raw_node in enumerate(section["nodes"]):
        placed = dict(raw_node)
        col = index % cols
        row = index // cols
        placed["x"] = x + SECTION_PADDING_X + col * (node_width + GRID_GAP_X)
        placed["y"] = y + SECTION_HEADER_HEIGHT + SECTION_PADDING_Y + row * (NODE_HEIGHT + GRID_GAP_Y)
        placed["width"] = node_width
        placed["height"] = NODE_HEIGHT
        placed_nodes.append(placed)
    return container, placed_nodes, height


def build_renderer_column() -> list[dict[str, Any]]:
    return [
        {
            "label": "Renderer / 入口与壳层",
            "header_prefix": "01",
            "header_text": "RENDERER",
            "cols": 4,
            "nodes": [
                node("r-index", "渲染宿主", "index.html", manual_status="已完成", palette="info", type_label="HTML", owner_paths=["src/renderer/index.html"], report_group="Renderer / 入口与壳层"),
                node("r-main", "React 启动", "main.tsx", manual_status="已完成", palette="info", type_label="ENTRY", owner_paths=["src/renderer/main.tsx"], report_group="Renderer / 入口与壳层"),
                node(
                    "r-app",
                    "全局工作台壳",
                    "App.tsx",
                    kind="double_rect",
                    manual_status="部分完成",
                    type_label="OWNER",
                    owner_paths=["src/renderer/App.tsx"],
                    status_note="docs/03-架构实现 指出 App.tsx 仍偏大，后续功能不应继续堆回壳层。",
                    report_group="Renderer / 入口与壳层",
                ),
                node(
                    "r-shell",
                    "壳层区块组合",
                    "AppShellSections.tsx",
                    kind="double_rect",
                    manual_status="部分完成",
                    type_label="OWNER",
                    owner_paths=["src/renderer/components/AppShellSections.tsx"],
                    status_note="p039 已完成壳层拆分，但该文件仍承接较多组合逻辑。",
                    report_group="Renderer / 入口与壳层",
                ),
                node(
                    "r-primitives",
                    "壳层基元",
                    "ShellPrimitives.tsx",
                    status_ids=["F-104", "F-105", "F-106", "F-108", "F-109", "INF-046"],
                    owner_paths=["src/renderer/components/ShellPrimitives.tsx"],
                    type_label="COMP",
                    report_group="Renderer / 入口与壳层",
                ),
                node(
                    "r-command",
                    "命令面板",
                    "CommandPalette.tsx",
                    status_ids=["F-103", "INF-047"],
                    owner_paths=["src/renderer/components/CommandPalette.tsx"],
                    type_label="COMP",
                    report_group="Renderer / 入口与壳层",
                ),
                node(
                    "r-stage",
                    "阶段徽标",
                    "StageBadge.tsx",
                    status_ids=["F-047", "F-048", "F-049"],
                    owner_paths=["src/renderer/components/StageBadge.tsx"],
                    type_label="COMP",
                    report_group="Renderer / 入口与壳层",
                ),
                node(
                    "r-overlay",
                    "浮层宿主",
                    "OverlayPortal.tsx",
                    status_ids=["F-104", "F-106"],
                    owner_paths=["src/renderer/components/OverlayPortal.tsx"],
                    type_label="COMP",
                    report_group="Renderer / 入口与壳层",
                ),
                node(
                    "r-hooks",
                    "域状态 Hook",
                    "useAppDomainStates.ts",
                    manual_status="已完成",
                    palette="info",
                    type_label="HOOK",
                    owner_paths=["src/renderer/hooks/useAppDomainStates.ts"],
                    status_note="p035 已把六类关键 domain state 从 App.tsx 下沉到 hook owner。",
                    report_group="Renderer / 入口与壳层",
                ),
                node(
                    "r-hook-types",
                    "域状态类型",
                    "app-domain-types.ts",
                    manual_status="已完成",
                    palette="info",
                    type_label="HOOK",
                    owner_paths=["src/renderer/hooks/app-domain-types.ts"],
                    report_group="Renderer / 入口与壳层",
                ),
                node(
                    "r-styles",
                    "界面皮肤",
                    "styles.css",
                    status_ids=["F-109", "INF-046"],
                    owner_paths=["src/renderer/styles.css"],
                    type_label="STYLE",
                    report_group="Renderer / 入口与壳层",
                ),
                node(
                    "r-vite",
                    "Vite 环境",
                    "vite-env.d.ts",
                    manual_status="已完成",
                    palette="info",
                    type_label="TYPE",
                    owner_paths=["src/renderer/vite-env.d.ts"],
                    report_group="Renderer / 入口与壳层",
                ),
                node(
                    "r-policy",
                    "模型策略预览",
                    "model-policy.ts",
                    status_ids=["F-058", "F-102"],
                    owner_paths=["src/renderer/lib/model-policy.ts"],
                    type_label="LIB",
                    report_group="Renderer / 入口与壳层",
                ),
            ],
        },
        {
            "label": "Renderer / 文档工作台",
            "header_prefix": "02",
            "header_text": "WORKBENCH",
            "cols": 4,
            "nodes": [
                node(
                    "r-filetree",
                    "文件树",
                    "FileTree.tsx",
                    status_ids=["F-018", "F-019", "F-020", "F-021", "F-022", "F-023", "F-024", "F-025", "F-026"],
                    owner_paths=["src/renderer/components/FileTree.tsx"],
                    type_label="COMP",
                    report_group="Renderer / 文档工作台",
                ),
                node(
                    "r-tabs",
                    "文档标签",
                    "DocumentTabs.tsx",
                    status_ids=["F-027", "F-028", "F-029", "INF-014"],
                    owner_paths=["src/renderer/components/DocumentTabs.tsx"],
                    type_label="COMP",
                    report_group="Renderer / 文档工作台",
                ),
                node(
                    "r-find",
                    "查找替换",
                    "FindReplaceBar.tsx",
                    status_ids=["F-031", "INF-013"],
                    owner_paths=["src/renderer/components/FindReplaceBar.tsx"],
                    type_label="COMP",
                    report_group="Renderer / 文档工作台",
                ),
                node(
                    "r-markdown",
                    "Markdown 渲染",
                    "MarkdownContent.tsx",
                    status_ids=["F-032", "F-033", "F-034", "F-035"],
                    owner_paths=["src/renderer/components/MarkdownContent.tsx"],
                    type_label="COMP",
                    report_group="Renderer / 文档工作台",
                ),
                node(
                    "r-mermaid",
                    "Mermaid 块",
                    "MermaidBlock.tsx",
                    status_ids=["F-036"],
                    owner_paths=["src/renderer/components/MermaidBlock.tsx"],
                    type_label="COMP",
                    report_group="Renderer / 文档工作台",
                ),
                node(
                    "r-mindmap",
                    "思维导图块",
                    "MindMapBlock.tsx",
                    status_ids=["F-037"],
                    owner_paths=["src/renderer/components/MindMapBlock.tsx"],
                    type_label="COMP",
                    report_group="Renderer / 文档工作台",
                ),
                node(
                    "r-preview",
                    "UI 预览块",
                    "UiPreviewBlock.tsx",
                    manual_status="已完成",
                    palette="info",
                    type_label="COMP",
                    owner_paths=["src/renderer/components/UiPreviewBlock.tsx"],
                    report_group="Renderer / 文档工作台",
                ),
                node(
                    "r-conflict",
                    "冲突对话框",
                    "ConflictDialog.tsx",
                    status_ids=["F-040", "F-142"],
                    owner_paths=["src/renderer/components/ConflictDialog.tsx"],
                    type_label="DIALOG",
                    report_group="Renderer / 文档工作台",
                ),
                node(
                    "r-protection",
                    "写回保护框",
                    "DocumentProtectionDialog.tsx",
                    status_ids=["F-142", "F-147"],
                    owner_paths=["src/renderer/components/DocumentProtectionDialog.tsx"],
                    type_label="DIALOG",
                    report_group="Renderer / 文档工作台",
                ),
            ],
        },
        {
            "label": "Renderer / 编排、资源、设置",
            "header_prefix": "03",
            "header_text": "EDITOR",
            "cols": 4,
            "nodes": [
                node(
                    "r-orch",
                    "编排工作区",
                    "OrchestrationWorkspace.tsx",
                    kind="double_rect",
                    status_ids=[
                        "F-059",
                        "F-061",
                        "F-062",
                        "F-063",
                        "F-064",
                        "F-065",
                        "F-066",
                        "F-067",
                        "F-068",
                        "F-069",
                        "F-070",
                        "F-071",
                        "F-072",
                        "F-073",
                        "F-074",
                        "F-075",
                        "F-076",
                        "F-077",
                        "F-078",
                        "F-079",
                        "F-080",
                        "F-081",
                        "F-082",
                        "F-083",
                        "F-084",
                        "F-085",
                        "F-086",
                        "F-087",
                        "F-088",
                        "F-089",
                        "F-091",
                        "F-143",
                        "F-145",
                    ],
                    owner_paths=["src/renderer/components/OrchestrationWorkspace.tsx"],
                    type_label="OWNER",
                    report_group="Renderer / 编排、资源、设置",
                ),
                node(
                    "r-template-page",
                    "模板中心页",
                    "TemplateCenterPage.tsx",
                    status_ids=["F-011", "F-012", "F-122", "F-123"],
                    owner_paths=["src/renderer/components/TemplateCenterPage.tsx"],
                    type_label="PAGE",
                    report_group="Renderer / 编排、资源、设置",
                ),
                node(
                    "r-template-dialog",
                    "模板中心弹窗",
                    "TemplateCenterDialog.tsx",
                    status_ids=["F-011", "F-012", "F-013", "F-122", "F-123"],
                    owner_paths=["src/renderer/components/TemplateCenterDialog.tsx"],
                    type_label="DIALOG",
                    report_group="Renderer / 编排、资源、设置",
                ),
                node(
                    "r-project-template",
                    "建工程向导",
                    "ProjectTemplateDialog.tsx",
                    status_ids=["F-006", "F-007", "F-008", "F-009"],
                    owner_paths=["src/renderer/components/ProjectTemplateDialog.tsx"],
                    type_label="DIALOG",
                    report_group="Renderer / 编排、资源、设置",
                ),
                node(
                    "r-save-template",
                    "保存模板框",
                    "SaveTemplateDialog.tsx",
                    status_ids=["F-014"],
                    owner_paths=["src/renderer/components/SaveTemplateDialog.tsx"],
                    type_label="DIALOG",
                    report_group="Renderer / 编排、资源、设置",
                ),
                node(
                    "r-resource",
                    "资源中心",
                    "ResourceCenterPage.tsx",
                    status_ids=["F-095", "F-096", "F-097", "F-098", "F-099", "F-100", "F-107", "F-146"],
                    owner_paths=["src/renderer/components/ResourceCenterPage.tsx"],
                    type_label="PAGE",
                    report_group="Renderer / 编排、资源、设置",
                ),
                node(
                    "r-provider",
                    "Provider 配置",
                    "ProviderProfilesDialog.tsx",
                    status_ids=["F-057", "F-101", "F-102"],
                    owner_paths=["src/renderer/components/ProviderProfilesDialog.tsx"],
                    type_label="DIALOG",
                    report_group="Renderer / 编排、资源、设置",
                ),
                node(
                    "r-package-url",
                    "远程包安装框",
                    "PackageUrlDialog.tsx",
                    status_ids=["F-097", "F-128"],
                    owner_paths=["src/renderer/components/PackageUrlDialog.tsx"],
                    type_label="DIALOG",
                    report_group="Renderer / 编排、资源、设置",
                ),
                node(
                    "r-settings",
                    "设置工作区",
                    "SettingsWorkspacePage.tsx",
                    status_ids=["F-057", "F-101", "F-102", "F-109"],
                    owner_paths=["src/renderer/components/SettingsWorkspacePage.tsx"],
                    type_label="PAGE",
                    report_group="Renderer / 编排、资源、设置",
                ),
            ],
        },
    ]


def build_boundary_ai_column() -> list[dict[str, Any]]:
    return [
        {
            "label": "Electron / Preload / IPC",
            "header_prefix": "04",
            "header_text": "IPC",
            "cols": 4,
            "nodes": [
                node(
                    "m-main",
                    "主进程入口",
                    "main.ts",
                    status_ids=["F-110", "INF-001"],
                    owner_paths=["src/main/main.ts"],
                    type_label="ENTRY",
                    report_group="Electron / Preload / IPC",
                ),
                node(
                    "m-window",
                    "窗口状态",
                    "window-state.ts",
                    status_ids=["INF-001", "INF-002", "F-105"],
                    owner_paths=["src/main/services/window-state.ts"],
                    type_label="BOOT",
                    report_group="Electron / Preload / IPC",
                ),
                node(
                    "m-preload",
                    "桥接预加载",
                    "preload.ts",
                    kind="hexagon",
                    manual_status="已完成",
                    palette="boundary",
                    type_label="PRELOAD",
                    owner_paths=["src/main/preload.ts"],
                    status_note="当前 preload 已收口为 DesktopApi 边界。",
                    report_group="Electron / Preload / IPC",
                ),
                node(
                    "m-ipc",
                    "IPC 壳层",
                    "ipc.ts",
                    kind="hexagon",
                    manual_status="已完成",
                    palette="boundary",
                    type_label="IPC",
                    owner_paths=["src/main/ipc.ts"],
                    status_note="p039 后 ipc.ts 只负责 registration shell。",
                    report_group="Electron / Preload / IPC",
                ),
                node(
                    "m-ipc-context",
                    "注册上下文",
                    "ipc/context.ts",
                    kind="hexagon",
                    manual_status="已完成",
                    palette="boundary",
                    type_label="CTX",
                    owner_paths=["src/main/ipc/context.ts"],
                    report_group="Electron / Preload / IPC",
                ),
                node(
                    "ipc-project",
                    "工程/文档通道",
                    "register-project-document-ipc.ts",
                    kind="hexagon",
                    status_ids=["F-015", "F-018", "F-027", "F-039", "F-040", "F-130"],
                    owner_paths=["src/main/ipc/register-project-document-ipc.ts"],
                    palette="boundary",
                    type_label="IPC",
                    report_group="Electron / Preload / IPC",
                ),
                node(
                    "ipc-settings",
                    "设置/会话通道",
                    "register-settings-session-ai-ipc.ts",
                    kind="hexagon",
                    status_ids=["F-043", "F-044", "F-101", "F-141", "F-148"],
                    owner_paths=["src/main/ipc/register-settings-session-ai-ipc.ts"],
                    palette="boundary",
                    type_label="IPC",
                    report_group="Electron / Preload / IPC",
                ),
                node(
                    "ipc-runtime",
                    "运行时通道",
                    "register-runtime-platform-ipc.ts",
                    kind="hexagon",
                    status_ids=["F-050", "F-054", "F-061", "F-091", "F-140", "F-144", "F-148"],
                    owner_paths=["src/main/ipc/register-runtime-platform-ipc.ts"],
                    palette="boundary",
                    type_label="IPC",
                    report_group="Electron / Preload / IPC",
                ),
                node(
                    "ipc-resource",
                    "资源/注册通道",
                    "register-resource-ipc.ts",
                    kind="hexagon",
                    status_ids=["F-011", "F-013", "F-095", "F-096", "F-101", "F-146"],
                    owner_paths=["src/main/ipc/register-resource-ipc.ts"],
                    palette="boundary",
                    type_label="IPC",
                    report_group="Electron / Preload / IPC",
                ),
                node(
                    "ipc-recent",
                    "最近记录通道",
                    "register-recent-system-ipc.ts",
                    kind="hexagon",
                    status_ids=["F-001", "F-002", "F-003", "F-015", "F-016"],
                    owner_paths=["src/main/ipc/register-recent-system-ipc.ts"],
                    palette="boundary",
                    type_label="IPC",
                    report_group="Electron / Preload / IPC",
                ),
            ],
        },
        {
            "label": "Main / 平台与资源注册",
            "header_prefix": "05",
            "header_text": "PLATFORM",
            "cols": 4,
            "nodes": [
                node(
                    "svc-platform",
                    "平台服务",
                    "platform-service.ts",
                    status_ids=["F-001", "F-005", "F-010", "F-011", "F-103"],
                    owner_paths=["src/main/services/platform-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 平台与资源注册",
                ),
                node(
                    "svc-template-reg",
                    "模板注册",
                    "template-registry-service.ts",
                    status_ids=["F-012", "F-013", "F-122", "F-123", "INF-029", "INF-059"],
                    owner_paths=["src/main/services/template-registry-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 平台与资源注册",
                ),
                node(
                    "svc-template-author",
                    "模板脚手架",
                    "template-authoring-service.ts",
                    status_ids=["F-014", "INF-030"],
                    owner_paths=["src/main/services/template-authoring-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 平台与资源注册",
                ),
                node(
                    "svc-skill-reg",
                    "Skill 注册",
                    "skill-registry-service.ts",
                    status_ids=["F-095", "F-096", "F-097", "F-098", "F-099", "INF-026"],
                    owner_paths=["src/main/services/skill-registry-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 平台与资源注册",
                ),
                node(
                    "svc-role-reg",
                    "角色包注册",
                    "role-package-registry-service.ts",
                    status_ids=["F-078", "F-079", "F-080", "F-116", "F-128", "INF-053", "INF-062"],
                    owner_paths=["src/main/services/role-package-registry-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 平台与资源注册",
                ),
                node(
                    "svc-resource-gov",
                    "资源治理",
                    "resource-governance-service.ts",
                    status_ids=["F-146", "INF-078"],
                    owner_paths=["src/main/services/resource-governance-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 平台与资源注册",
                ),
            ],
        },
        {
            "label": "Main / 工程与文档链路",
            "header_prefix": "06",
            "header_text": "PROJECT",
            "cols": 4,
            "nodes": [
                node(
                    "svc-project",
                    "工程服务",
                    "project-service.ts",
                    kind="double_rect",
                    status_ids=[
                        "F-015",
                        "F-016",
                        "F-017",
                        "F-018",
                        "F-019",
                        "F-020",
                        "F-021",
                        "F-022",
                        "F-023",
                        "F-024",
                        "F-025",
                        "F-026",
                        "F-027",
                        "F-028",
                        "F-029",
                        "F-030",
                        "F-039",
                        "F-040",
                        "INF-003",
                        "INF-005",
                        "INF-006",
                        "INF-014",
                    ],
                    owner_paths=["src/main/services/project-service.ts"],
                    type_label="OWNER",
                    report_group="Main / 工程与文档链路",
                ),
                node(
                    "svc-doc-change",
                    "文档变更分析",
                    "document-change-service.ts",
                    status_ids=["F-130", "F-131", "INF-063", "INF-064"],
                    owner_paths=["src/main/services/document-change-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 工程与文档链路",
                ),
                node(
                    "svc-doc-snapshot",
                    "快照恢复",
                    "document-snapshot-service.ts",
                    status_ids=["F-147", "INF-079"],
                    owner_paths=["src/main/services/document-snapshot-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 工程与文档链路",
                ),
                node(
                    "svc-doc-diff",
                    "差异计算",
                    "document-diff.ts",
                    status_ids=["F-142"],
                    owner_paths=["src/main/services/document-diff.ts"],
                    type_label="UTIL",
                    report_group="Main / 工程与文档链路",
                ),
                node(
                    "svc-merge",
                    "人机合并",
                    "human-ai-merge-service.ts",
                    status_ids=["F-142", "INF-074"],
                    owner_paths=["src/main/services/human-ai-merge-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 工程与文档链路",
                ),
            ],
        },
        {
            "label": "Main / AI 会话与生成",
            "header_prefix": "07",
            "header_text": "AI",
            "cols": 4,
            "nodes": [
                node(
                    "svc-store",
                    "设置/会话存储",
                    "store.ts",
                    status_ids=["F-043", "F-044", "F-057", "F-101", "INF-002", "INF-016"],
                    owner_paths=["src/main/services/store.ts"],
                    type_label="STORE",
                    report_group="Main / AI 会话与生成",
                ),
                node(
                    "svc-ai",
                    "AI 调用",
                    "ai-service.ts",
                    kind="double_rect",
                    status_ids=["F-045", "F-050", "F-051", "F-052", "F-053", "F-054", "F-055", "F-056", "F-057", "F-058", "INF-018"],
                    owner_paths=["src/main/services/ai-service.ts"],
                    type_label="OWNER",
                    report_group="Main / AI 会话与生成",
                ),
                node(
                    "svc-router",
                    "模型路由",
                    "model-router.ts",
                    status_ids=["F-055", "F-058", "INF-019", "INF-022"],
                    owner_paths=["src/main/services/model-router.ts"],
                    type_label="SERVICE",
                    report_group="Main / AI 会话与生成",
                ),
                node(
                    "svc-structured",
                    "结构化生成",
                    "structured-generation-service.ts",
                    status_ids=["F-050", "F-052", "F-053", "INF-020", "INF-021", "INF-024"],
                    owner_paths=["src/main/services/structured-generation-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / AI 会话与生成",
                ),
                node(
                    "svc-compaction",
                    "会话压缩",
                    "conversation-compaction-service.ts",
                    status_ids=["F-140", "INF-071"],
                    owner_paths=["src/main/services/conversation-compaction-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / AI 会话与生成",
                ),
                node(
                    "svc-flowchat",
                    "对话编排规划",
                    "conversation-flow-service.ts",
                    status_ids=["F-125", "F-126", "F-127", "INF-060", "INF-061"],
                    owner_paths=["src/main/services/conversation-flow-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / AI 会话与生成",
                ),
            ],
        },
    ]


def build_runtime_planned_column() -> list[dict[str, Any]]:
    return [
        {
            "label": "Main / 运行编排与知识底座",
            "header_prefix": "08",
            "header_text": "RUNTIME",
            "cols": 4,
            "nodes": [
                node(
                    "svc-orchestrator",
                    "工作区编排器",
                    "workspace-orchestrator.ts",
                    kind="double_rect",
                    status_ids=["F-047", "F-048", "F-049", "F-050", "F-051", "F-052", "F-053", "F-125", "F-126", "F-127", "INF-023", "INF-024", "INF-060", "INF-061"],
                    owner_paths=["src/main/services/workspace-orchestrator.ts"],
                    type_label="OWNER",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-runtime",
                    "运行时主服务",
                    "runtime-service.ts",
                    kind="double_rect",
                    status_ids=["F-054", "F-091", "F-140", "F-141", "F-144", "F-148", "F-149", "INF-017", "INF-075", "INF-076", "INF-080", "INF-081"],
                    owner_paths=["src/main/services/runtime-service.ts"],
                    type_label="OWNER",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-runtime-assets",
                    "运行时资产",
                    "runtime-asset-service.ts",
                    status_ids=["F-087", "F-088", "F-089", "F-090", "F-091", "F-092", "F-093", "F-094", "F-143", "INF-031", "INF-032", "INF-034", "INF-035", "INF-036", "INF-052", "INF-072", "INF-073"],
                    owner_paths=["src/main/services/runtime-asset-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-capability",
                    "能力运行时",
                    "capability-runtime.ts",
                    status_ids=["F-081", "F-082", "F-083", "F-149", "INF-025", "INF-027", "INF-028", "INF-081"],
                    owner_paths=["src/main/services/capability-runtime.ts"],
                    type_label="SERVICE",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-export",
                    "交付导出",
                    "delivery-export-service.ts",
                    status_ids=["F-092", "F-093", "INF-044", "INF-045"],
                    owner_paths=["src/main/services/delivery-export-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-runtime-errors",
                    "运行错误语义",
                    "runtime-errors.ts",
                    status_ids=["F-054", "F-104", "F-149", "INF-043"],
                    owner_paths=["src/main/services/runtime-errors.ts"],
                    type_label="UTIL",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-index",
                    "知识索引",
                    "knowledge-index-service.ts",
                    status_ids=["F-117", "F-121", "INF-054", "INF-057"],
                    owner_paths=["src/main/services/knowledge-index-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-retrieval",
                    "混合检索",
                    "hybrid-retrieval-service.ts",
                    status_ids=["F-118", "F-119", "F-120", "INF-055", "INF-056"],
                    owner_paths=["src/main/services/hybrid-retrieval-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-provenance",
                    "来源追溯",
                    "provenance-service.ts",
                    status_ids=["F-120", "F-141", "INF-058"],
                    owner_paths=["src/main/services/provenance-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-budget",
                    "预算治理",
                    "runtime-budget-governor.ts",
                    status_ids=["F-141", "F-148", "INF-080"],
                    owner_paths=["src/main/services/runtime-budget-governor.ts"],
                    type_label="SERVICE",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-evidence",
                    "证据存储",
                    "evidence-store-service.ts",
                    status_ids=["F-144", "F-149", "INF-076"],
                    owner_paths=["src/main/services/evidence-store-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 运行编排与知识底座",
                ),
                node(
                    "svc-sideeffect",
                    "副作用治理",
                    "side-effect-governance-service.ts",
                    status_ids=["F-149", "INF-081"],
                    owner_paths=["src/main/services/side-effect-governance-service.ts"],
                    type_label="SERVICE",
                    report_group="Main / 运行编排与知识底座",
                ),
            ],
        },
        {
            "label": "文档待补 / UI 与运行时链路",
            "header_prefix": "09",
            "header_text": "PLANNED",
            "cols": 4,
            "nodes": [
                node("gap-provenance-ui", "引用下钻界面", "逐条来源解释界面", manual_status="未完成", type_label="PLAN", tags=["docs/03-架构实现 4.2"], status_note="docs/03-架构实现 明确要求补上 citation 级逐条 drill-down 与更细粒度 provenance 解释界面。", report_group="文档待补 / UI 与运行时链路"),
                node("gap-invalidation-ui", "失效传播面板", "ArtifactInvalidationList", status_ids=["F-143", "INF-073"], type_label="PLAN", report_group="文档待补 / UI 与运行时链路"),
                node("gap-durable-ui", "长任务恢复栏", "DurableRunToolbar", status_ids=["F-144", "INF-075"], type_label="PLAN", report_group="文档待补 / UI 与运行时链路"),
                node("gap-trace-ui", "运行追踪面板", "RunTracePanel", status_ids=["INF-076"], type_label="PLAN", report_group="文档待补 / UI 与运行时链路"),
                node("gap-patch-preview", "补丁预览弹窗", "PatchPreviewModal", status_ids=["F-142", "INF-072"], type_label="PLAN", report_group="文档待补 / UI 与运行时链路"),
                node("gap-approval-ui", "审批预览入口", "Approval / SideEffect UI", status_ids=["F-145", "F-149", "INF-077", "INF-081"], type_label="PLAN", report_group="文档待补 / UI 与运行时链路"),
                node("gap-merge-modal", "合并决策弹窗", "MergeDecisionModal", status_ids=["F-142", "INF-074"], type_label="PLAN", report_group="文档待补 / UI 与运行时链路"),
                node("gap-context-ui", "上下文包精选界面", "固定/排除/细粒度选择", manual_status="未完成", type_label="PLAN", tags=["docs/03-架构实现 4.2"], status_note="docs/03-架构实现 明确要求补上用户可操作的上下文包固定、排除与精细化选择界面。", report_group="文档待补 / UI 与运行时链路"),
            ],
        },
        {
            "label": "文档待补 / 治理与恢复服务",
            "header_prefix": "10",
            "header_text": "RECOVERY",
            "cols": 4,
            "nodes": [
                node("gap-patch-service", "补丁合并服务", "ArtifactPatchMergeService", status_ids=["F-142", "INF-072"], type_label="PLAN", report_group="文档待补 / 治理与恢复服务"),
                node("gap-invalidation-service", "失效传播服务", "ArtifactInvalidationPropagationService", status_ids=["F-143", "INF-073"], type_label="PLAN", report_group="文档待补 / 治理与恢复服务"),
                node("gap-durable-service", "耐久恢复协调器", "DurableRunCoordinator", status_ids=["F-144", "INF-075"], type_label="PLAN", report_group="文档待补 / 治理与恢复服务"),
                node("gap-tracing-service", "追踪评测服务", "RuntimeTracingEvaluationService", status_ids=["INF-076"], type_label="PLAN", report_group="文档待补 / 治理与恢复服务"),
                node("gap-sideeffect-service", "副作用策略引擎", "LocalSideEffectPolicyEngine", status_ids=["F-149", "INF-081"], type_label="PLAN", report_group="文档待补 / 治理与恢复服务"),
                node("gap-trust-service", "本地包信任验证", "LocalPackageTrustVerifier", status_ids=["F-146", "INF-078"], type_label="PLAN", report_group="文档待补 / 治理与恢复服务"),
                node("gap-review-gate", "评审门协调器", "ReviewGateCoordinator", manual_status="未完成", type_label="PLAN", tags=["docs/03-架构实现"], status_note="docs/03-架构实现 已定义 ReviewGateCoordinator / ReadinessReviewService，但当前代码尚未形成完整准入层服务。", report_group="文档待补 / 治理与恢复服务"),
                node("gap-parity", "文档代码测试审计", "DocCodeTestParityService", manual_status="未完成", type_label="PLAN", tags=["docs/03-架构实现"], status_note="docs/03-架构实现 已定义 DocCodeTestParityAuditor，但当前仅有一致性检查基础，没有完整 parity service。", report_group="文档待补 / 治理与恢复服务"),
                node("gap-error-service", "可执行错误服务", "ActionableErrorService", manual_status="未完成", type_label="PLAN", tags=["docs/03-架构实现"], status_note="docs/03-架构实现 明确要求错误对象包含恢复入口与下一步动作，当前仍未完整系统化。", report_group="文档待补 / 治理与恢复服务"),
                node("gap-recovery-route", "恢复路径服务", "RecoveryRouteService", manual_status="未完成", type_label="PLAN", tags=["docs/03-架构实现"], status_note="docs/03-架构实现 定义了 RecoveryCoordinator / RecoveryRouteService，但当前仅有局部恢复基础。", report_group="文档待补 / 治理与恢复服务"),
            ],
        },
        {
            "label": "文档待补 / 规则与沉淀中心",
            "header_prefix": "11",
            "header_text": "RULES",
            "cols": 4,
            "nodes": [
                node("gap-rule-registry", "规则作用域解析", "RuleRegistryAndScopeResolver", status_ids=["F-132", "F-133", "F-134", "INF-065"], type_label="PLAN", report_group="文档待补 / 规则与沉淀中心"),
                node("gap-rule-conflict", "规则冲突评估", "RuleConflictEvaluator", status_ids=["F-134", "F-135", "INF-066"], type_label="PLAN", report_group="文档待补 / 规则与沉淀中心"),
                node("gap-knowledge-graph", "知识图构建", "ProjectKnowledgeGraphBuilder", status_ids=["F-136", "INF-067"], type_label="PLAN", report_group="文档待补 / 规则与沉淀中心"),
                node("gap-accumulation", "沉淀条目存储", "AccumulationEntryStore", status_ids=["F-137", "F-139", "INF-068"], type_label="PLAN", report_group="文档待补 / 规则与沉淀中心"),
                node("gap-distillation", "沉淀提升流水线", "DistillationPromotionPipeline", status_ids=["F-138", "F-139", "INF-069"], type_label="PLAN", report_group="文档待补 / 规则与沉淀中心"),
            ],
        },
    ]


def build_top_columns() -> list[list[dict[str, Any]]]:
    return [build_renderer_column(), build_boundary_ai_column(), build_runtime_planned_column()]


def build_bottom_sections() -> list[dict[str, Any]]:
    return [
        {
            "label": "Shared / 契约、转换、包格式",
            "header_prefix": "12",
            "header_text": "SHARED",
            "cols": 4,
            "nodes": [
                node(
                    "shared-types",
                    "核心类型契约",
                    "types.ts",
                    kind="double_rect",
                    manual_status="已完成",
                    palette="info",
                    type_label="SCHEMA",
                    owner_paths=["src/shared/types.ts"],
                    status_note="types.ts 已承载 ContextPack、EvidencePackage、ActionableErrorRecord 等核心跨层契约。",
                    report_group="Shared / 契约、转换、包格式",
                ),
                node(
                    "shared-flow-validator",
                    "Flow 校验",
                    "flow-validator.ts",
                    status_ids=["F-066", "F-067", "F-068", "F-069", "F-070", "INF-033"],
                    owner_paths=["src/shared/flow-validator.ts"],
                    type_label="SCHEMA",
                    report_group="Shared / 契约、转换、包格式",
                ),
                node(
                    "shared-artifact-validator",
                    "工件校验",
                    "artifact-validators.ts",
                    status_ids=["F-088", "F-089", "F-091", "INF-035", "INF-072"],
                    owner_paths=["src/shared/artifact-validators.ts"],
                    type_label="SCHEMA",
                    report_group="Shared / 契约、转换、包格式",
                ),
                node(
                    "shared-consistency",
                    "一致性检查",
                    "consistency.ts",
                    manual_status="部分完成",
                    type_label="SCHEMA",
                    owner_paths=["src/shared/consistency.ts"],
                    status_note="已有 consistency check，但 docs/03-架构实现 定义的完整 DocCodeTestParityService 仍未系统化。",
                    report_group="Shared / 契约、转换、包格式",
                ),
                node(
                    "shared-conv-flow",
                    "对话转 Flow",
                    "conversation-flow.ts",
                    status_ids=["F-125", "F-126", "F-127", "INF-060", "INF-061"],
                    owner_paths=["src/shared/conversation-flow.ts"],
                    type_label="SCHEMA",
                    report_group="Shared / 契约、转换、包格式",
                ),
                node(
                    "shared-runtime-template",
                    "运行时模板",
                    "runtime-template.ts",
                    status_ids=["F-087", "F-088", "F-090", "F-092", "F-093", "F-094", "INF-034", "INF-036"],
                    owner_paths=["src/shared/runtime-template.ts"],
                    type_label="SCHEMA",
                    report_group="Shared / 契约、转换、包格式",
                ),
                node(
                    "shared-template-package",
                    "模板包格式",
                    "template-package.ts",
                    status_ids=["F-013", "F-122", "F-123"],
                    owner_paths=["src/shared/template-package.ts"],
                    type_label="SCHEMA",
                    report_group="Shared / 契约、转换、包格式",
                ),
                node(
                    "shared-skill-package",
                    "Skill 包格式",
                    "skill-package.ts",
                    status_ids=["F-095", "F-096", "F-097", "F-098", "F-099"],
                    owner_paths=["src/shared/skill-package.ts"],
                    type_label="SCHEMA",
                    report_group="Shared / 契约、转换、包格式",
                ),
                node(
                    "shared-role-package",
                    "角色包格式",
                    "role-package.ts",
                    status_ids=["F-078", "F-079", "F-080", "F-116", "F-128"],
                    owner_paths=["src/shared/role-package.ts"],
                    type_label="SCHEMA",
                    report_group="Shared / 契约、转换、包格式",
                ),
                node(
                    "shared-ui-preview",
                    "UI 预览契约",
                    "ui-preview.ts",
                    manual_status="已完成",
                    palette="info",
                    type_label="SCHEMA",
                    owner_paths=["src/shared/ui-preview.ts"],
                    report_group="Shared / 契约、转换、包格式",
                ),
                node(
                    "shared-openspec",
                    "OpenSpec 工具",
                    "openspec.ts",
                    status_ids=["F-093"],
                    owner_paths=["src/shared/openspec.ts"],
                    type_label="UTIL",
                    report_group="Shared / 契约、转换、包格式",
                ),
            ],
        },
        {
            "label": "Data / 本地数据与外部对象",
            "header_prefix": "13",
            "header_text": "DATA",
            "cols": 4,
            "nodes": [
                node("data-project", "工程目录", "项目文档 / assets / flows", kind="folder", manual_status="已完成", palette="storage", type_label="FS", report_group="Data / 本地数据与外部对象"),
                node("data-runtime", ".project/runtime", "run / context / checkpoints", kind="folder", manual_status="已完成", palette="storage", type_label="FS", report_group="Data / 本地数据与外部对象"),
                node("data-evidence", ".project/evidence", "reviews / runs / errors", kind="cylinder", manual_status="已完成", palette="evidence", type_label="STORE", report_group="Data / 本地数据与外部对象"),
                node(
                    "data-template-json",
                    "模板包 JSON",
                    "src/shared/template-packages/*.json",
                    kind="folder",
                    manual_status="已完成",
                    palette="storage",
                    type_label="DATA",
                    owner_paths=["src/shared/template-packages/software-factory.json", "src/shared/template-packages/gstack-office-hours.json"],
                    report_group="Data / 本地数据与外部对象",
                ),
                node(
                    "data-manifest-json",
                    "模板清单 JSON",
                    "src/shared/template-manifests/*.json",
                    kind="folder",
                    manual_status="已完成",
                    palette="storage",
                    type_label="DATA",
                    owner_paths=["src/shared/template-manifests/software-factory.json", "src/shared/template-manifests/gstack-office-hours.json"],
                    report_group="Data / 本地数据与外部对象",
                ),
                node("data-packages", "本地模板/技能/角色目录", "install / import / trust", kind="folder", status_ids=["F-097", "F-123", "F-128", "F-146"], palette="storage", type_label="DATA", report_group="Data / 本地数据与外部对象"),
                node("data-provider", "模型提供方", "Ollama / DeepSeek / OpenAI Compatible", kind="bot", manual_status="已完成", palette="boundary", type_label="MODEL", report_group="Data / 本地数据与外部对象", report=False, show_status_tag=False),
            ],
        },
    ]


def clone_section(section: dict[str, Any], cols: int | None = None) -> dict[str, Any]:
    cloned = dict(section)
    cloned["nodes"] = list(section["nodes"])
    if cols is not None:
        cloned["cols"] = cols
    return cloned


def build_layout() -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    full_width = CANVAS_WIDTH - (PAGE_MARGIN_X * 2)
    half_gap = 40
    half_width = (full_width - half_gap) // 2

    containers: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = [
        {
            "id": "user",
            "kind": "user_avatar",
            "x": (CANVAS_WIDTH - 80) // 2,
            "y": 52,
            "width": 80,
            "height": 80,
            "label": "用户",
            "sublabel": "",
            "type_label": "INPUT",
            "fill": PALETTES["info"]["fill"],
            "stroke": PALETTES["info"]["stroke"],
            "accent_fill": PALETTES["info"]["accent_fill"],
            "line_stroke": PALETTES["info"]["line_stroke"],
            "tags": [],
        }
    ]

    row_gap = 54
    cursor_y = 150

    renderer_sections = build_renderer_column()
    renderer_rows = [
        [(clone_section(renderer_sections[0], cols=5), PAGE_MARGIN_X, full_width)],
        [
            (clone_section(renderer_sections[1], cols=4), PAGE_MARGIN_X, half_width),
            (clone_section(renderer_sections[2], cols=4), PAGE_MARGIN_X + half_width + half_gap, half_width),
        ],
    ]
    for row in renderer_rows:
        row_height = 0
        for section, x, width in row:
            container, placed_nodes, height = place_section(section, x, cursor_y, width)
            containers.append(container)
            nodes.extend(placed_nodes)
            row_height = max(row_height, height)
        cursor_y += row_height + row_gap

    boundary_sections = build_boundary_ai_column()
    runtime_sections = build_runtime_planned_column()
    bottom_sections = build_bottom_sections()

    ipc_row = [(clone_section(boundary_sections[0], cols=5), PAGE_MARGIN_X, full_width)]
    row_height = 0
    for section, x, width in ipc_row:
        container, placed_nodes, height = place_section(section, x, cursor_y, width)
        containers.append(container)
        nodes.extend(placed_nodes)
        row_height = max(row_height, height)
    cursor_y += row_height + row_gap

    main_rows = [
        [
            (clone_section(boundary_sections[1], cols=3), PAGE_MARGIN_X, half_width),
            (clone_section(runtime_sections[0], cols=4), PAGE_MARGIN_X + half_width + half_gap, half_width),
        ],
        [
            (clone_section(boundary_sections[2], cols=3), PAGE_MARGIN_X, half_width),
            (clone_section(boundary_sections[3], cols=3), PAGE_MARGIN_X + half_width + half_gap, half_width),
        ],
    ]
    for row in main_rows:
        row_height = 0
        for section, x, width in row:
            container, placed_nodes, height = place_section(section, x, cursor_y, width)
            containers.append(container)
            nodes.extend(placed_nodes)
            row_height = max(row_height, height)
        cursor_y += row_height + row_gap

    planned_rows = [
        [
            (clone_section(runtime_sections[1], cols=4), PAGE_MARGIN_X, half_width),
            (clone_section(runtime_sections[2], cols=4), PAGE_MARGIN_X + half_width + half_gap, half_width),
        ],
        [(clone_section(runtime_sections[3], cols=5), PAGE_MARGIN_X, full_width)],
    ]
    for row in planned_rows:
        row_height = 0
        for section, x, width in row:
            container, placed_nodes, height = place_section(section, x, cursor_y, width)
            containers.append(container)
            nodes.extend(placed_nodes)
            row_height = max(row_height, height)
        cursor_y += row_height + row_gap

    bottom_rows = [
        [(clone_section(bottom_sections[0], cols=5), PAGE_MARGIN_X, full_width)],
        [(clone_section(bottom_sections[1], cols=4), PAGE_MARGIN_X, full_width)],
    ]
    row_height = 0
    for row in bottom_rows:
        row_height = 0
        for section, x, width in row:
            container, placed_nodes, height = place_section(section, x, cursor_y, width)
            containers.append(container)
            nodes.extend(placed_nodes)
            row_height = max(row_height, height)
        cursor_y += row_height + row_gap

    canvas_height = cursor_y - row_gap + 60
    return containers, nodes, canvas_height


def arrow(
    source: str,
    target: str,
    *,
    flow: str = "control",
    label: str = "",
    source_port: str | None = None,
    target_port: str | None = None,
    corridor_x: list[float] | None = None,
    corridor_y: list[float] | None = None,
    routing_padding: float | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {"source": source, "target": target, "flow": flow}
    if label:
        data["label"] = label
    if source_port:
        data["source_port"] = source_port
    if target_port:
        data["target_port"] = target_port
    if corridor_x:
        data["corridor_x"] = corridor_x
    if corridor_y:
        data["corridor_y"] = corridor_y
    if routing_padding is not None:
        data["routing_padding"] = routing_padding
    return data


def build_arrows() -> list[dict[str, Any]]:
    return [
        arrow("user", "r-main", label="进入", source_port="bottom", target_port="top"),

        # Renderer bootstrap
        arrow("r-index", "r-main", flow="neutral", source_port="right", target_port="left"),
        arrow("r-vite", "r-main", flow="neutral", source_port="right", target_port="left"),
        arrow("r-main", "r-app", source_port="right", target_port="left"),
        arrow("r-app", "r-shell", flow="neutral", source_port="right", target_port="left"),
        arrow("r-app", "r-hooks", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-hooks", "r-hook-types", flow="neutral", source_port="right", target_port="left"),
        arrow("r-shell", "r-primitives", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-primitives", "r-command", flow="neutral", source_port="right", target_port="left"),
        arrow("r-primitives", "r-stage", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-primitives", "r-overlay", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-primitives", "r-styles", flow="neutral", source_port="bottom", target_port="top"),

        # Renderer composition
        arrow("r-shell", "r-filetree", flow="neutral", source_port="left", target_port="right"),
        arrow("r-shell", "r-orch", flow="neutral", source_port="right", target_port="left"),
        arrow("r-shell", "r-resource", flow="neutral", source_port="right", target_port="left"),
        arrow("r-shell", "r-settings", flow="neutral", source_port="right", target_port="left"),
        arrow("r-filetree", "r-tabs", flow="neutral", source_port="right", target_port="left"),
        arrow("r-tabs", "r-markdown", flow="neutral", source_port="right", target_port="left"),
        arrow("r-find", "r-markdown", flow="neutral", source_port="right", target_port="left"),
        arrow("r-markdown", "r-mermaid", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-markdown", "r-mindmap", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-markdown", "r-preview", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-markdown", "r-conflict", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-markdown", "r-protection", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-resource", "r-template-page", flow="neutral", source_port="left", target_port="right"),
        arrow("r-template-page", "r-template-dialog", flow="neutral", source_port="right", target_port="left"),
        arrow("r-template-dialog", "r-project-template", flow="neutral", source_port="right", target_port="left"),
        arrow("r-template-dialog", "r-save-template", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-resource", "r-package-url", flow="neutral", source_port="bottom", target_port="top"),
        arrow("r-settings", "r-provider", flow="neutral", source_port="right", target_port="left"),
        arrow("r-provider", "r-policy", flow="neutral", source_port="bottom", target_port="top"),

        # Renderer -> IPC
        arrow("r-app", "m-preload", label="DesktopApi", source_port="bottom", target_port="top"),
        arrow("r-filetree", "ipc-project", source_port="bottom", target_port="top"),
        arrow("r-orch", "ipc-runtime", source_port="bottom", target_port="top"),
        arrow("r-resource", "ipc-resource", source_port="bottom", target_port="top"),
        arrow("r-settings", "ipc-settings", source_port="bottom", target_port="top"),

        # Electron boundary
        arrow("m-main", "m-window", flow="neutral", source_port="right", target_port="left"),
        arrow("m-window", "m-preload", flow="neutral", source_port="right", target_port="left"),
        arrow("m-preload", "m-ipc", label="桥接", source_port="right", target_port="left"),
        arrow("m-ipc", "m-ipc-context", flow="neutral", source_port="right", target_port="left"),
        arrow("m-ipc", "ipc-project", source_port="bottom", target_port="top"),
        arrow("m-ipc", "ipc-settings", source_port="bottom", target_port="top"),
        arrow("m-ipc", "ipc-runtime", source_port="bottom", target_port="top"),
        arrow("m-ipc", "ipc-resource", source_port="bottom", target_port="top"),
        arrow("m-ipc", "ipc-recent", source_port="bottom", target_port="top"),

        # IPC -> main services
        arrow("ipc-recent", "svc-platform", source_port="bottom", target_port="top"),
        arrow("ipc-resource", "svc-template-reg", source_port="bottom", target_port="top"),
        arrow("ipc-resource", "svc-skill-reg", source_port="bottom", target_port="top"),
        arrow("ipc-resource", "svc-role-reg", source_port="bottom", target_port="top"),
        arrow("ipc-project", "svc-project", source_port="bottom", target_port="top"),
        arrow("ipc-settings", "svc-store", source_port="bottom", target_port="top"),
        arrow("ipc-runtime", "svc-orchestrator", source_port="bottom", target_port="top"),
        arrow("ipc-runtime", "svc-runtime", source_port="bottom", target_port="top"),

        # Main internal dependencies
        arrow("svc-platform", "svc-template-reg", flow="neutral", source_port="right", target_port="left"),
        arrow("svc-platform", "svc-skill-reg", flow="neutral", source_port="bottom", target_port="top"),
        arrow("svc-skill-reg", "svc-role-reg", flow="neutral", source_port="right", target_port="left"),
        arrow("svc-template-reg", "svc-template-author", flow="neutral", source_port="right", target_port="left"),
        arrow("svc-template-reg", "svc-resource-gov", flow="neutral", source_port="bottom", target_port="top"),
        arrow("svc-project", "svc-doc-change", flow="neutral", source_port="right", target_port="left"),
        arrow("svc-project", "svc-doc-snapshot", flow="neutral", source_port="right", target_port="left"),
        arrow("svc-doc-change", "svc-doc-diff", flow="neutral", source_port="bottom", target_port="top"),
        arrow("svc-doc-diff", "svc-merge", flow="neutral", source_port="right", target_port="left"),
        arrow("svc-store", "svc-ai", source_port="right", target_port="left"),
        arrow("svc-store", "svc-compaction", flow="neutral", source_port="bottom", target_port="top"),
        arrow("svc-flowchat", "svc-structured", flow="neutral", source_port="left", target_port="right"),
        arrow("svc-structured", "svc-ai", flow="neutral", source_port="top", target_port="bottom"),
        arrow("svc-ai", "svc-router", source_port="right", target_port="left"),
        arrow("svc-orchestrator", "svc-runtime", source_port="right", target_port="left"),
        arrow("svc-runtime", "svc-runtime-errors", flow="neutral", source_port="bottom", target_port="top"),
        arrow("svc-runtime", "svc-capability", source_port="right", target_port="left"),
        arrow("svc-runtime", "svc-runtime-assets", source_port="right", target_port="left"),
        arrow("svc-runtime-assets", "svc-export", flow="write", source_port="bottom", target_port="top"),
        arrow("svc-runtime", "svc-index", flow="read", source_port="bottom", target_port="top"),
        arrow("svc-index", "svc-retrieval", flow="read", source_port="right", target_port="left"),
        arrow("svc-retrieval", "svc-provenance", flow="read", source_port="bottom", target_port="top"),
        arrow("svc-runtime", "svc-budget", source_port="bottom", target_port="top"),
        arrow("svc-runtime", "svc-evidence", flow="write", source_port="bottom", target_port="top"),
        arrow("svc-runtime", "svc-sideeffect", source_port="bottom", target_port="top"),

        # Shared contracts
        arrow("shared-types", "m-preload", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-types", "r-hooks", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-flow-validator", "r-orch", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-artifact-validator", "svc-runtime-assets", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-conv-flow", "svc-flowchat", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-runtime-template", "svc-runtime-assets", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-template-package", "svc-template-reg", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-skill-package", "svc-skill-reg", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-role-package", "svc-role-reg", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-ui-preview", "r-preview", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-openspec", "svc-export", flow="read", source_port="top", target_port="bottom"),
        arrow("shared-consistency", "gap-parity", flow="neutral", source_port="top", target_port="bottom"),

        # Data and persistence
        arrow("svc-project", "data-project", flow="write", source_port="bottom", target_port="top"),
        arrow("svc-runtime", "data-runtime", flow="write", source_port="bottom", target_port="top"),
        arrow("svc-evidence", "data-evidence", flow="write", source_port="bottom", target_port="top"),
        arrow("svc-template-reg", "data-template-json", flow="read", source_port="bottom", target_port="top"),
        arrow("svc-template-reg", "data-manifest-json", flow="read", source_port="bottom", target_port="top"),
        arrow("svc-skill-reg", "data-packages", flow="write", source_port="bottom", target_port="top"),
        arrow("svc-role-reg", "data-packages", flow="write", source_port="bottom", target_port="top"),
        arrow("svc-resource-gov", "data-packages", flow="write", source_port="bottom", target_port="top"),
        arrow("svc-ai", "data-provider", source_port="bottom", target_port="top"),
        arrow("svc-export", "data-project", flow="write", source_port="bottom", target_port="top"),

        # Planned / unfinished architecture
        arrow("svc-provenance", "gap-provenance-ui", flow="neutral", source_port="bottom", target_port="top"),
        arrow("svc-retrieval", "gap-context-ui", flow="neutral", source_port="bottom", target_port="top"),
        arrow("svc-doc-diff", "gap-patch-service", flow="neutral", source_port="bottom", target_port="top"),
        arrow("gap-patch-service", "gap-patch-preview", flow="neutral", source_port="left", target_port="right"),
        arrow("gap-patch-preview", "gap-merge-modal", flow="neutral", source_port="left", target_port="right"),
        arrow("svc-runtime-assets", "gap-invalidation-service", flow="neutral", source_port="bottom", target_port="top"),
        arrow("gap-invalidation-service", "gap-invalidation-ui", flow="neutral", source_port="left", target_port="right"),
        arrow("svc-runtime", "gap-durable-service", flow="neutral", source_port="bottom", target_port="top"),
        arrow("gap-durable-service", "gap-durable-ui", flow="neutral", source_port="left", target_port="right"),
        arrow("svc-evidence", "gap-tracing-service", flow="neutral", source_port="bottom", target_port="top"),
        arrow("gap-tracing-service", "gap-trace-ui", flow="neutral", source_port="left", target_port="right"),
        arrow("svc-sideeffect", "gap-sideeffect-service", flow="neutral", source_port="bottom", target_port="top"),
        arrow("gap-sideeffect-service", "gap-approval-ui", flow="neutral", source_port="left", target_port="right"),
        arrow("svc-resource-gov", "gap-trust-service", flow="neutral", source_port="bottom", target_port="top"),
        arrow("gap-trust-service", "gap-approval-ui", flow="neutral", source_port="left", target_port="right"),
        arrow("svc-runtime", "gap-review-gate", flow="neutral", source_port="bottom", target_port="top"),
        arrow("gap-review-gate", "gap-parity", flow="neutral", source_port="right", target_port="left"),
        arrow("svc-runtime-errors", "gap-error-service", flow="neutral", source_port="bottom", target_port="top"),
        arrow("gap-error-service", "gap-recovery-route", flow="neutral", source_port="right", target_port="left"),
        arrow("gap-rule-registry", "gap-rule-conflict", flow="neutral", source_port="right", target_port="left"),
        arrow("gap-rule-conflict", "gap-knowledge-graph", flow="neutral", source_port="right", target_port="left"),
        arrow("gap-accumulation", "gap-distillation", flow="neutral", source_port="right", target_port="left"),
    ]


def build_legend() -> list[dict[str, Any]]:
    return [
        {"flow": "control", "label": "主调用链"},
        {"flow": "read", "label": "共享契约/知识输入"},
        {"flow": "write", "label": "落盘/证据/导出"},
        {"flow": "neutral", "label": "结构归属/待补关联"},
    ]


def export_png(root: Path, svg_output: Path, png_output: Path) -> str | None:
    if cairosvg is not None:
        try:
            cairosvg.svg2png(bytestring=svg_output.read_bytes(), write_to=str(png_output), output_width=CANVAS_WIDTH)
            return "cairosvg"
        except Exception:
            pass

    node_script = r"""
const { chromium } = require('playwright');
const path = require('node:path');
(async () => {
  const svgPath = process.argv[1];
  const pngPath = process.argv[2];
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1280 }, deviceScaleFactor: 2 });
  await page.goto('file:///' + path.resolve(svgPath).replace(/\\/g, '/'), { waitUntil: 'load', timeout: 60000 });
  await page.locator('svg').screenshot({ path: pngPath, timeout: 120000 });
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
"""
    result = subprocess.run(
        ["node", "-e", node_script, str(svg_output), str(png_output)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode == 0 and png_output.exists():
        return "playwright"
    return None


def main() -> None:
    root = repo_root()
    generator = load_generator()
    status_by_id, counts = parse_status_table(root / "docs" / "01-需求与PRD" / "03-功能范围与优先级.md")
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    containers, raw_nodes, canvas_height = build_layout()
    resolved_nodes: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []
    for raw_node in raw_nodes:
        if raw_node["id"] == "user":
            raw_node["type_label"] = localize_type_label(raw_node.get("type_label", ""))
            resolved_nodes.append(raw_node)
            continue
        svg_node, report_row = resolve_node(raw_node, status_by_id, root)
        resolved_nodes.append(svg_node)
        if report_row:
            report_rows.append(report_row)

    diagram_data = {
        "style": 1,
        "width": CANVAS_WIDTH,
        "height": canvas_height,
        "viewBox": f"0 0 {CANVAS_WIDTH} {canvas_height}",
        "title": "Software Factory 系统设计架构图",
        "subtitle": "基于 docs/03-架构实现 当前架构、docs/03-架构实现 系统设计、docs/01-需求与PRD/03-功能范围与优先级.md 状态源与当前 src owner 自动生成",
        "legend_box": True,
        "legend_position": "bottom-left",
        "footer": (
            f"扫描日期 {datetime.now().strftime('%Y-%m-%d')} | "
            f"状态统计：已完成 {counts['ALL']['已完成']} / 部分完成 {counts['ALL']['部分完成']} / 未完成 {counts['ALL']['未完成']} | "
            "未完成模块来自 docs/03-架构实现 4.2 与 docs/03-架构实现"
        ),
        "containers": containers,
        "nodes": resolved_nodes,
        "arrows": build_arrows(),
        "legend": build_legend(),
    }

    svg_output = output_dir / SVG_NAME
    png_output = output_dir / PNG_NAME
    data_output = output_dir / DATA_NAME
    report_output = output_dir / REPORT_NAME

    data_output.write_text(json.dumps(diagram_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")
    svg_content = generator.build_svg("architecture", diagram_data)
    svg_output.write_text(svg_content, encoding="utf-8")
    png_method = export_png(root, svg_output, png_output)
    build_report(report_rows, report_output)

    print(f"SVG: {svg_output}")
    print(f"PNG: {png_output if png_method else 'skipped'}")
    print(f"DATA: {data_output}")
    print(f"REPORT: {report_output}")


if __name__ == "__main__":
    main()
