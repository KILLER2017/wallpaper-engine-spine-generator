# -*- coding: utf-8 -*-
"""
Wallpaper Engine (Web / Spine) 壁纸构建核心。

把一套 Spine 三件套（.skel / .atlas / .png）+ 可选背景图，
按模板生成一个可直接导入 Wallpaper Engine 的 Web 网页壁纸工程目录。

设计约定：
- 三件套文件名必须保持原名（.atlas 内部记录的贴图名与 .png 强绑定，不可重命名）。
- 运行时模板 template/spine-webgl-3.8.js 为 Spine 3.8 WebGL 构建，兼容这份游戏变体 skel。
- 主动画挂 track 0 循环；时长为 0 的姿势 / 表情切片作为叠加层挂 track 1，下拉切换。
"""

import dataclasses
import json
import os
import shutil
import subprocess
import sys
import zipfile
from typing import List, Optional


def _base_dir() -> str:
    """定位程序资源根目录：源码运行取本文件目录；PyInstaller 打包后取解压目录或 exe 旁目录。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


TEMPLATE_DIR = os.path.join(_base_dir(), "template")
RUNTIME_JS = "spine-webgl-3.8.js"


def _tools_dir() -> str:
    """随包附带工具链根目录：源码运行=脚本目录/tools；打包后=程序目录/tools。"""
    return os.path.join(_base_dir(), "tools")


def _cli_env() -> Optional[dict]:
    """
    调用 CLI 的环境块。若随包附带了便携 .NET 运行时（tools/dotnet），
    则把 DOTNET_ROOT 指向它并关闭全局多级查找，使目标机无需安装系统 .NET；
    没有附带运行时则返回 None，沿用当前进程环境（依赖系统已装 .NET）。
    """
    dotnet = os.path.join(_tools_dir(), "dotnet")
    if os.path.isdir(os.path.join(dotnet, "dotnet.exe")) or \
            os.path.isdir(os.path.join(dotnet, "host")):
        env = os.environ.copy()
        env["DOTNET_ROOT"] = dotnet
        env["DOTNET_MULTILEVEL_LOOKUP"] = "0"
        return env
    return None


@dataclasses.dataclass
class WallpaperConfig:
    title: str
    skel_name: str
    atlas_name: str
    png_name: str
    anim: str
    expressions: List[str] = dataclasses.field(default_factory=list)
    background_name: Optional[str] = None
    zoom: int = 105
    x: int = 50
    y: int = 46
    speed: float = 1.0
    fps_limit: str = "0"
    align_h: str = "center"
    align_v: str = "center"


# ---------------------------------------------------------------------------
# CLI 查询
# ---------------------------------------------------------------------------

CLI_EXE = "SpineViewerCLI.exe"


def find_cli() -> str:
    """
    自动探测 SpineViewerCLI.exe，返回第一个存在的路径；都找不到返回空串。

    探测顺序：
    1. 随包附带的便携 CLI（tools/SpineViewer/<exe>）；
    2. 环境变量 SPINE_VIEWER_CLI；
    3. 程序目录向上逐级的 tools/SpineViewer/<exe>；
    4. 常见固定位置（LOCALAPPDATA、用户主目录下的 tools/SpineViewer）。
    """
    bundled = os.path.join(_tools_dir(), "SpineViewer", CLI_EXE)
    if os.path.exists(bundled):
        return bundled

    env = os.environ.get("SPINE_VIEWER_CLI", "").strip()
    if env and os.path.exists(env):
        return env

    roots: List[str] = []
    if getattr(sys, "frozen", False):
        roots.append(os.path.dirname(sys.executable))
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            roots.append(meipass)
    roots.append(os.path.dirname(os.path.abspath(__file__)))

    candidates: List[str] = []
    for root in roots:
        cur = root
        for _ in range(6):
            candidates.append(os.path.join(cur, "tools", "SpineViewer", CLI_EXE))
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent

    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        candidates.append(os.path.join(local, "tools", "SpineViewer", CLI_EXE))
    candidates.append(os.path.join(os.path.expanduser("~"), "tools", "SpineViewer", CLI_EXE))

    for c in candidates:
        if c and os.path.exists(c):
            return c
    return ""


def query_animations(cli_path: str, skel_path: str) -> List[dict]:
    """调用 SpineViewerCLI 查询动画列表，返回 [{"name":..., "duration":...}, ...]。"""
    if not cli_path or not os.path.exists(cli_path):
        raise FileNotFoundError("未找到 SpineViewerCLI：" + str(cli_path))
    if not os.path.exists(skel_path):
        raise FileNotFoundError("未找到 skel 文件：" + skel_path)

    proc = subprocess.run(
        [cli_path, "query", skel_path, "--animation"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_cli_env(),
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    anims: List[dict] = []
    in_section = False
    for line in out.splitlines():
        if "Animations" in line:
            in_section = True
            continue
        if in_section and line.strip().startswith("<<<"):
            break
        if not in_section:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name = parts[0].strip()
        if not name or name == "Name":
            continue
        try:
            duration = float(parts[1].strip())
        except ValueError:
            continue
        anims.append({"name": name, "duration": duration})
    return anims


def export_preview(cli_path: str, src_skel: str, src_atlas: str, anim: str,
                   out_png: str, max_resolution: int = 2560, log=print) -> bool:
    """用 CLI 导出主动画首帧作为预览图。成功返回 True。"""
    if not cli_path or not os.path.exists(cli_path):
        log("⚠ 未配置 CLI，跳过预览帧导出。")
        return False
    cmd = [
        cli_path, "export", src_skel,
        "--atlas", src_atlas,
        "--format", "Png",
        "--animations", anim,
        "--duration", "0",
        "--max-resolution", str(max_resolution),
        "--margin", "0",
        "--output", out_png,
        "--no-progress",
    ]
    log("· 导出预览帧：" + anim)
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=_cli_env())
    if proc.returncode != 0 or not os.path.exists(out_png):
        log("⚠ 预览帧导出失败：" + (proc.stderr or proc.stdout or "未知错误").strip())
        return False
    return True


# ---------------------------------------------------------------------------
# 模板渲染
# ---------------------------------------------------------------------------

def _render_template(tpl_name: str, mapping: dict) -> str:
    with open(os.path.join(TEMPLATE_DIR, tpl_name), "r", encoding="utf-8") as f:
        text = f.read()
    for key, value in mapping.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def _build_project_json(cfg: WallpaperConfig) -> dict:
    props = {
        "schemecolor": {
            "order": 0,
            "text": "ui_browse_properties_scheme_color",
            "type": "color",
            "value": "0.08 0.06 0.05",
        },
        "zoom": {
            "index": 0, "max": 200, "min": 50, "order": 100, "step": 1,
            "text": "缩放（%）", "type": "slider", "value": cfg.zoom,
        },
        "speed": {
            "index": 1, "fraction": True, "max": 2, "min": 0.2, "order": 101,
            "precision": 2, "step": 0.05, "text": "播放速度（倍速）",
            "type": "slider", "value": cfg.speed,
        },
    }

    order = 102
    if cfg.expressions:
        options = [{"label": "待机", "value": "normal"}]
        options += [{"label": e, "value": e} for e in cfg.expressions]
        props["expression"] = {
            "index": 2, "options": options, "order": order,
            "text": "表情 / 姿势", "type": "combo", "value": "normal",
        }
        order += 1

    props["fpsLimit"] = {
        "index": 3,
        "options": [
            {"label": "跟随全局", "value": "0"},
            {"label": "30 FPS", "value": "30"},
            {"label": "60 FPS", "value": "60"},
            {"label": "120 FPS", "value": "120"},
        ],
        "order": order, "text": "帧率限制", "type": "combo", "value": cfg.fps_limit,
    }
    order += 1
    props["alignH"] = {
        "index": 4,
        "options": [
            {"label": "靠左", "value": "left"},
            {"label": "居中", "value": "center"},
            {"label": "靠右", "value": "right"},
        ],
        "order": order, "text": "水平对齐", "type": "combo", "value": cfg.align_h,
    }
    order += 1
    props["alignV"] = {
        "index": 5,
        "options": [
            {"label": "靠上", "value": "top"},
            {"label": "居中", "value": "center"},
            {"label": "靠下", "value": "bottom"},
        ],
        "order": order, "text": "垂直对齐", "type": "combo", "value": cfg.align_v,
    }
    order += 1
    props["x"] = {
        "index": 6, "max": 100, "min": 0, "order": order, "step": 1,
        "text": "水平位置（%）", "type": "slider", "value": cfg.x,
    }
    order += 1
    props["y"] = {
        "index": 7, "max": 100, "min": 0, "order": order, "step": 1,
        "text": "垂直位置（%）", "type": "slider", "value": cfg.y,
    }

    return {
        "contentrating": "Everyone",
        "description": cfg.title,
        "file": "index.html",
        "general": {"properties": props},
        "preview": "preview.png",
        "ratingsex": "none",
        "ratingviolence": "none",
        "tags": ["Anime"],
        "title": cfg.title,
        "type": "Web",
        "version": 1,
    }


# ---------------------------------------------------------------------------
# 构建主流程
# ---------------------------------------------------------------------------

def build_wallpaper(cfg: WallpaperConfig, src_skel: str, src_atlas: str, src_png: str,
                    src_bg: Optional[str], out_dir: str, cli_path: str = "",
                    make_preview: bool = True, preview_size: int = 2560,
                    make_zip: bool = False, preview_source: Optional[str] = None,
                    log=print) -> dict:
    """
    生成壁纸工程目录。返回 {"out_dir":..., "zip":..., "warnings":[...]}。
    """
    warnings: List[str] = []

    # 1. 校验源文件
    for label, path in (("skel", src_skel), ("atlas", src_atlas), ("png", src_png)):
        if not path or not os.path.exists(path):
            raise FileNotFoundError("缺少 " + label + " 源文件：" + str(path))

    assets_dir = os.path.join(out_dir, "assets")
    js_dir = os.path.join(out_dir, "js")
    os.makedirs(assets_dir, exist_ok=True)
    os.makedirs(js_dir, exist_ok=True)

    # 2. 复制运行时
    shutil.copy2(os.path.join(TEMPLATE_DIR, RUNTIME_JS),
                 os.path.join(js_dir, RUNTIME_JS))
    log("· 复制 Spine 运行时")

    # 3. 渲染 app.js
    app_js = _render_template("app.js.tpl", {
        "SKEL": cfg.skel_name, "ATLAS": cfg.atlas_name, "PNG": cfg.png_name,
        "ANIM": cfg.anim, "ZOOM": cfg.zoom, "X": cfg.x, "Y": cfg.y,
        "SPEED": cfg.speed, "FPSLIMIT": cfg.fps_limit,
        "ALIGNH": cfg.align_h, "ALIGNV": cfg.align_v,
    })
    with open(os.path.join(js_dir, "app.js"), "w", encoding="utf-8") as f:
        f.write(app_js)
    log("· 生成 js/app.js")

    # 4. 渲染 index.html
    if cfg.background_name:
        bg_css = "#14100d url(assets/%s) center/cover no-repeat" % cfg.background_name
    else:
        bg_css = "#14100d"
    index_html = _render_template("index.html.tpl", {
        "TITLE": cfg.title, "BG": bg_css,
    })
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    log("· 生成 index.html")

    # 5. project.json
    project = _build_project_json(cfg)
    with open(os.path.join(out_dir, "project.json"), "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent="\t")
    log("· 生成 project.json")

    # 6. 拷贝三件套（保持原名）
    shutil.copy2(src_skel, os.path.join(assets_dir, cfg.skel_name))
    shutil.copy2(src_atlas, os.path.join(assets_dir, cfg.atlas_name))
    shutil.copy2(src_png, os.path.join(assets_dir, cfg.png_name))
    log("· 拷贝三件套到 assets/")

    # 7. 背景图
    if src_bg and os.path.exists(src_bg):
        shutil.copy2(src_bg, os.path.join(assets_dir, cfg.background_name))
        log("· 拷贝背景图：" + cfg.background_name)

    # 8. 预览图
    preview_path = os.path.join(out_dir, "preview.png")
    if make_preview and cli_path:
        export_preview(cli_path, src_skel, src_atlas, cfg.anim,
                       preview_path, preview_size, log)
    if not os.path.exists(preview_path) and preview_source and os.path.exists(preview_source):
        shutil.copy2(preview_source, preview_path)
        log("· 使用提供的预览图")
    if not os.path.exists(preview_path):
        warnings.append("缺少 preview.png：请手动放一张 16:9 预览图到工程根目录。")
        log("⚠ 缺少 preview.png")

    # 9. 结构与 JSON 校验
    _validate(out_dir, warnings, log)

    # 10. 打包 zip（平铺）
    zip_path = None
    if make_zip:
        zip_path = os.path.join(os.path.dirname(out_dir.rstrip("\\/")),
                                os.path.basename(out_dir) + "_wallpaper.zip")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(out_dir):
                for name in files:
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, out_dir).replace("\\", "/")
                    zf.write(full, rel)
        log("· 打包：" + os.path.basename(zip_path))

    return {"out_dir": out_dir, "zip": zip_path, "warnings": warnings}


def _validate(out_dir: str, warnings: List[str], log) -> None:
    required = ["project.json", "index.html", "js/app.js",
                 "js/" + RUNTIME_JS]
    for rel in required:
        if not os.path.exists(os.path.join(out_dir, rel)):
            raise FileNotFoundError("产物缺失：" + rel)
    with open(os.path.join(out_dir, "project.json"), "r", encoding="utf-8") as f:
        json.load(f)
    assets = os.listdir(os.path.join(out_dir, "assets"))
    if len(assets) < 3:
        warnings.append("assets/ 内素材不足三件套，请检查。")
    log("· 校验通过：工程结构完整，project.json 合法。")
