from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_existing_recipes(path: Path) -> List[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_recipes(path: Path, recipes: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(recipes, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip())


def dedup_by_name(recipes: List[dict]) -> List[dict]:
    seen = set()
    out = []
    for r in recipes:
        n = normalize_name(r.get("name", ""))
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(r)
    return out


def parse_ingredients_block(lines: List[str]) -> Dict[str, str]:
    """
    尽力解析：
    - 支持 "- 鸡蛋 2 个" / "- 鸡蛋：2个" / "鸡蛋 2个"
    - 解析不出来的行会被忽略
    """
    ingredients: Dict[str, str] = {}

    for raw in lines:
        s = raw.strip().lstrip("-").strip()
        if not s:
            continue

        # 形式1：食材：用量
        if "：" in s:
            a, b = s.split("：", 1)
            a, b = a.strip(), b.strip()
            if a:
                ingredients[a] = b or "适量/按需"
            continue

        # 形式2：食材 用量（用空格分割）
        parts = re.split(r"\s+", s, maxsplit=1)
        if len(parts) == 2:
            name, qty = parts[0].strip(), parts[1].strip()
            if name:
                ingredients[name] = qty or "适量/按需"
            continue

        # 形式3：只有食材名
        if s:
            ingredients[s] = "适量/按需"

    return ingredients


def parse_steps_block(lines: List[str]) -> List[str]:
    steps = []
    for raw in lines:
        s = raw.strip()
        s = re.sub(r"^\d+[\.\、]\s*", "", s)  # 去掉 1. / 1、
        s = s.lstrip("-").strip()
        if s:
            steps.append(s)
    return steps


def split_sections(md_text: str) -> Dict[str, List[str]]:
    """
    非严格 Markdown 解析：按二级标题/常见关键字切分
    """
    lines = md_text.splitlines()

    sections: Dict[str, List[str]] = {}
    current = "body"
    sections[current] = []

    header_re = re.compile(r"^\s{0,3}#{1,6}\s*(.+?)\s*$")
    for line in lines:
        m = header_re.match(line)
        if m:
            title = m.group(1).strip().lower()
            # 常见标题归一化
            if "食材" in title or "材料" in title or "原料" in title:
                current = "ingredients"
            elif "步骤" in title or "做法" in title or "制作" in title:
                current = "steps"
            else:
                current = f"h:{title}"
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)

    return sections


def guess_title(md_text: str, fallback: str) -> str:
    # 优先取第一个 Markdown 标题
    for line in md_text.splitlines():
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            return normalize_name(m.group(1))
    # 否则用文件名
    return normalize_name(fallback)


def parse_recipe_md(md_path: Path) -> Tuple[dict | None, str | None]:
    """
    返回：(recipe_dict 或 None, error_message 或 None)
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        return None, f"read_error: {e}"

    title = guess_title(text, md_path.stem)

    sections = split_sections(text)

    ing_lines = sections.get("ingredients", [])
    step_lines = sections.get("steps", [])

    ingredients = parse_ingredients_block(ing_lines)
    steps = parse_steps_block(step_lines)

    # 兜底：如果没有明确 ingredients/steps 标题，尝试从 body 中猜
    if not ingredients:
        body = sections.get("body", [])
        # 找类似“食材/材料”关键字后面的若干行
        for i, line in enumerate(body):
            if any(k in line for k in ["食材", "材料", "原料"]):
                ingredients = parse_ingredients_block(body[i + 1 : i + 30])
                break

    if not steps:
        body = sections.get("body", [])
        for i, line in enumerate(body):
            if any(k in line for k in ["步骤", "做法", "制作"]):
                steps = parse_steps_block(body[i + 1 : i + 80])
                break

    if not ingredients or not steps:
        return None, "missing_ingredients_or_steps"

    return {
        "name": title,
        "ingredients": ingredients,
        "steps": steps,
    }, None


def find_md_files(repo_dir: Path) -> List[Path]:
    # HowToCook 常见目录是 dishes/，但我们做宽松扫描：找 repo 下所有 .md（排除 README、docs）
    md_files = []
    for p in repo_dir.rglob("*.md"):
        rel = str(p.relative_to(repo_dir)).lower()
        if rel.endswith("readme.md"):
            continue
        if any(rel.startswith(prefix) for prefix in ["docs/", ".github/", "site/", "build/"]):
            continue
        md_files.append(p)
    return md_files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--howtocook-repo", required=True, help="HowToCook 仓库本地路径（你 git clone 下来的目录）")
    ap.add_argument("--out", default="data/recipes.json", help="输出到你的项目 recipes.json 路径")
    ap.add_argument("--max", type=int, default=0, help="最多导入多少条（0=不限制）")
    args = ap.parse_args()

    repo_dir = Path(args.howtocook_repo).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()

    existing = load_existing_recipes(out_path)
    existing_names = {normalize_name(r.get("name", "")) for r in existing if isinstance(r, dict)}

    md_files = find_md_files(repo_dir)

    imported: List[dict] = []
    skipped: List[Tuple[str, str]] = []

    for md in md_files:
        recipe, err = parse_recipe_md(md)
        if recipe is None:
            skipped.append((str(md), err or "unknown"))
            continue

        n = normalize_name(recipe["name"])
        if n in existing_names:
            continue

        imported.append(recipe)
        existing_names.add(n)

        if args.max and len(imported) >= args.max:
            break

    merged = dedup_by_name(existing + imported)
    save_recipes(out_path, merged)

    print(f"[OK] scanned_md_files={len(md_files)} imported={len(imported)} merged_total={len(merged)} out={out_path}")
    if skipped:
        print(f"[WARN] skipped={len(skipped)} (showing first 30)")
        for p, reason in skipped[:30]:
            print(f"  - {p} :: {reason}")


if __name__ == "__main__":
    main()