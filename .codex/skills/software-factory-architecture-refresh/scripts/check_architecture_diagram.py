from __future__ import annotations

import json
import sys
from pathlib import Path


EXPECTED_CONTAINER_MINIMUMS = {
    "工作台": 9,
    "渲染层": 13,
    "编辑器": 9,
    "进程边界": 10,
    "平台层": 6,
    "工程层": 5,
    "智能层": 6,
    "运行时": 12,
    "待建设": 8,
    "治理恢复": 10,
    "规则沉淀": 5,
    "共享契约": 11,
    "数据层": 7,
}

FORBIDDEN_CONTAINER_HEADERS = {
    "WORKBENCH",
    "RENDERER",
    "EDITOR",
    "IPC",
    "PLATFORM",
    "PROJECT",
    "AI",
    "RUNTIME",
    "PLANNED",
    "RECOVERY",
    "RULES",
    "SHARED",
    "DATA",
}

FORBIDDEN_TYPE_LABELS = {
    "INPUT",
    "ENTRY",
    "OWNER",
    "COMP",
    "DIALOG",
    "PAGE",
    "SERVICE",
    "PLAN",
    "SCHEMA",
    "DATA",
    "FS",
    "MODEL",
    "PRELOAD",
    "BOOT",
    "CTX",
    "IPC",
    "HOOK",
    "STYLE",
    "TYPE",
    "LIB",
    "UTIL",
    "STORE",
    "HTML",
}

MAX_WIDTH_HEIGHT_RATIO = 1.15
MAX_EXTRA_WIDE_HORIZONTAL_EDGES = 6
MIN_TOTAL_NODES = 112
MIN_TOTAL_ARROWS = 122
MIN_TOTAL_CONTAINERS = 13


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def load_data(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def count_nodes_in_container(container: dict, nodes: list[dict]) -> int:
    x1 = container["x"]
    y1 = container["y"]
    x2 = x1 + container["width"]
    y2 = y1 + container["height"]
    return sum(1 for node in nodes if x1 <= node["x"] < x2 and y1 <= node["y"] < y2)


def main() -> int:
    root = repo_root()
    data_path = root / "artifacts" / "architecture" / "software-factory-architecture.data.json"
    png_path = root / "artifacts" / "architecture" / "software-factory-architecture.png"
    report_path = root / "artifacts" / "architecture" / "software-factory-architecture-status.md"

    failures: list[str] = []

    if not data_path.exists():
        fail(failures, f"缺少数据文件: {data_path}")
    if not png_path.exists():
        fail(failures, f"缺少 PNG 文件: {png_path}")
    if not report_path.exists():
        fail(failures, f"缺少状态摘要: {report_path}")
    if failures:
        for item in failures:
            print(f"FAIL: {item}")
        return 1

    data = load_data(data_path)
    nodes = data["nodes"]
    arrows = data["arrows"]
    containers = data["containers"]

    ratio = data["width"] / data["height"]
    if ratio > MAX_WIDTH_HEIGHT_RATIO:
        fail(failures, f"画布过宽: ratio={ratio:.3f} > {MAX_WIDTH_HEIGHT_RATIO}")

    if len(nodes) < MIN_TOTAL_NODES:
        fail(failures, f"节点总数回退: {len(nodes)} < {MIN_TOTAL_NODES}")
    if len(arrows) < MIN_TOTAL_ARROWS:
        fail(failures, f"连线总数回退: {len(arrows)} < {MIN_TOTAL_ARROWS}")
    if len(containers) < MIN_TOTAL_CONTAINERS:
        fail(failures, f"分区总数回退: {len(containers)} < {MIN_TOTAL_CONTAINERS}")

    container_headers = [container["header_text"] for container in containers]
    invalid_headers = [header for header in container_headers if header in FORBIDDEN_CONTAINER_HEADERS]
    if invalid_headers:
        fail(failures, f"存在未中文化分区标题: {', '.join(sorted(set(invalid_headers)))}")

    invalid_type_labels = sorted(
        {
            node["type_label"]
            for node in nodes
            if node.get("type_label") in FORBIDDEN_TYPE_LABELS
        }
    )
    if invalid_type_labels:
        fail(failures, f"存在未中文化类型徽标: {', '.join(invalid_type_labels)}")

    node_map = {node["id"]: node for node in nodes}
    degree = {node["id"]: 0 for node in nodes}
    extra_wide_edges: list[str] = []
    for arrow in arrows:
        degree[arrow["source"]] += 1
        degree[arrow["target"]] += 1
        source = node_map[arrow["source"]]
        target = node_map[arrow["target"]]
        source_x = source["x"] + (source["width"] / 2)
        target_x = target["x"] + (target["width"] / 2)
        if abs(source_x - target_x) > 1400:
            extra_wide_edges.append(f"{arrow['source']}->{arrow['target']}")

    zero_degree = [node_map[node_id]["label"] for node_id, value in degree.items() if value == 0]
    if zero_degree:
        fail(failures, f"存在未连线模块: {', '.join(zero_degree)}")

    if len(extra_wide_edges) > MAX_EXTRA_WIDE_HORIZONTAL_EDGES:
        sample = ", ".join(extra_wide_edges[:6])
        fail(
            failures,
            f"超长横向跨区线过多: {len(extra_wide_edges)} > {MAX_EXTRA_WIDE_HORIZONTAL_EDGES}; 示例: {sample}",
        )

    container_counts = {}
    for container in containers:
        header = container["header_text"]
        container_counts[header] = count_nodes_in_container(container, nodes)

    for header, minimum in EXPECTED_CONTAINER_MINIMUMS.items():
        actual = container_counts.get(header, 0)
        if actual < minimum:
            fail(failures, f"{header} 节点数回退: {actual} < {minimum}")

    print(f"画布比例: {ratio:.3f}")
    print(f"节点/连线/分区: {len(nodes)} / {len(arrows)} / {len(containers)}")
    print("分区节点数:")
    for header in EXPECTED_CONTAINER_MINIMUMS:
        print(f"- {header}: {container_counts.get(header, 0)}")

    if failures:
        print("")
        print("自检失败:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("")
    print("自检通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
