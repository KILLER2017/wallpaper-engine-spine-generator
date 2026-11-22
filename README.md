# WE Web 壁纸生成器（Spine → Wallpaper Engine · 桌面 GUI）

把一套 Spine 三件套（`.skel` / `.atlas` / `.png`）一键生成可直接导入 **Wallpaper Engine** 的 **Web 网页壁纸**工程：桌面窗口操作，后端实时渲染 Spine 模型循环播放待机动画，不是视频文件。

## 一、运行环境

**分发版（推荐，零依赖）**：打包产物是一个文件夹 `壁纸生成器/`，里面已自带：

- Python 运行时（PyInstaller 封装，目标机**无需安装 Python**）；
- 便携 .NET 8.0.21 运行时（`tools/dotnet/`，目标机**无需安装系统 .NET**）；
- SpineViewerCLI 及其依赖（`tools/SpineViewer/`，已裁掉用不到的 ffmpeg）；
- Spine 3.8 WebGL 运行时（`template/spine-webgl-3.8.js`）。

拷到别的 Windows 64 位机器，解压后双击 `壁纸生成器.exe` 即可，不需要再下载任何运行时或 CLI。

**源码运行（改代码时用）**：需要带完整 Tcl/Tk 的 **Python 3.12**（本机为 `D:\Program Files\Python312\python.exe`），仅用标准库，无需 pip 装第三方包。注意 Doubao 沙箱内嵌的 Python 3.13 缺少 Tcl/Tk 脚本库，tkinter 无法初始化。

## 二、目录结构

源码目录：

```
wallpaper_toolkit/
├── gui.py                  # 桌面界面（tkinter）：文件选择 / 动画查询 / 属性 / 日志
├── builder.py              # 构建核心：CLI 定位 / 环境注入 / 渲染模板 / 生成工程 / 导出预览 / 打包校验
├── 启动壁纸生成器.bat       # 脚本方式启动（调用系统 Python 3.12 运行 gui.py）
├── README.md
├── template/
│   ├── spine-webgl-3.8.js  # 内置 Spine 3.8 WebGL 运行时（固定复用）
│   ├── app.js.tpl          # 渲染循环 / 暂停回调 / 属性解析 / 表情叠加 模板
│   └── index.html.tpl      # 页面骨架模板
├── tools/                  # 本地第三方工具链（不入库，见下方“仓库内容”）
│   ├── dotnet/             # 便携 .NET 8.0.21 运行时
│   └── SpineViewer/        # SpineViewerCLI + 依赖 DLL（无 ffmpeg）
└── dist/壁纸生成器/         # 打包产物（onedir 文件夹，已入库）
    ├── 壁纸生成器.exe
    └── _internal/          # 封装的 Python 运行时、template/、tools/ 副本
```

## 二·五、仓库内容与第三方许可

- 仓库收录：自研源码（`gui.py` / `builder.py`）、`template/` 模板、`dist/` 打包成品。
- **不入库**：`tools/`（第三方 CLI 与 .NET 运行时，与 `dist/_internal/tools/` 内副本重复，本地保留即可）；`output/` 解包素材与生成壁纸（版权归游戏官方，不随仓库分发）。
- `dist/` 与 `tools/` 内包含的 SpineViewerCLI、.NET 运行时、SFML、SkiaSharp 等第三方组件，版权与许可归各自所有者；二次分发前请核对对应许可证。游戏角色素材仅限本人私下使用，请勿公开上传工坊或商用。

## 三、启动方式

**方式一（分发版，推荐）**：解压产物文件夹，双击里面的 `壁纸生成器.exe`。整个文件夹要保持完整，不要只把 exe 单独拷出来（`_internal/` 里有运行时和工具链）。

**方式二（脚本 + 启动器）**：在源码目录双击 `启动壁纸生成器.bat`（调用系统 Python 3.12）。

**方式三（命令行）**：

```bash
"D:\Program Files\Python312\python.exe" gui.py
```

> 若 Python 3.12 装在别的路径，改 `启动壁纸生成器.bat` 里的 `PY` 变量即可。

## 四、界面操作步骤

1. **CLI 路径**：默认已自动定位随包内置的 `tools/SpineViewer/SpineViewerCLI.exe`，无需手动配置。若改用外部 CLI，可在顶部「浏览…」选择；也可用环境变量 `SPINE_VIEWER_CLI` 指定。
2. **选择三件套**：浏览 `.skel`，同目录同名的 `.atlas` / `.png` 会自动补齐，可手动改；背景图可选填（`.jpg` / `.png`，cover 铺底避免边缘露黑）。
3. **查询动画**：点「查询动画」，调用 CLI 读取模型：
   - **主动画（循环）**：时长 > 0 的动画，下拉选一个作为待机主轨道。
   - **表情 / 姿势切片**：时长 = 0 的静态切片，默认全选，可取消；生成后在 WE 右侧面板以下拉方式叠加切换。
4. **填写默认属性**：标题、缩放、速度、水平 / 垂直对齐、位置百分比。这些是默认值，导入 WE 后仍可在右侧面板实时调整。
5. **选择输出目录**，勾选是否「CLI 导出预览帧」「同时打包 zip」，点「生成壁纸」。日志区显示每一步结果与告警。

## 五、生成的工程结构

```
<输出目录>/
├── project.json            # WE 元数据（type Web，含缩放/速度/帧率/对齐/位置/表情下拉属性）
├── index.html              # 壁纸页面（canvas + 加载提示）
├── preview.png             # 预览图（CLI 导出首帧，或手动放入）
├── js/
│   ├── spine-webgl-3.8.js
│   └── app.js
└── assets/
    ├── <模型>.skel
    ├── <模型>.atlas
    ├── <模型>.png
    └── background.jpg      # 若提供了背景图
```

打包的 zip 为平铺结构（`project.json` / `index.html` 位于压缩包根），可直接在 WE 里「从文件打开」或解压后指向 `index.html`。

## 六、导入 Wallpaper Engine

1. WE → 左下角 **创建壁纸 / Create Wallpaper**，类型选 **网页 / Webpage**。
2. 路径指向生成目录的 `index.html`（或直接把整个文件夹拖进 WE）。
3. 保存启用。右侧属性面板可调：缩放、播放速度、帧率限制、水平 / 垂直对齐、位置细调、表情 / 姿势下拉。

## 七、核心 API（脚本化调用）

`builder.py` 不依赖桌面界面，可在自己的脚本里直接调用：

```python
import builder

cfg = builder.WallpaperConfig(
    title="角色-壁纸",
    skel_name="xxx.skel", atlas_name="xxx.atlas", png_name="xxx.png",
    anim="normal",                       # 主动画名
    expressions=["1", "2"],             # 时长 0 的表情切片，可空列表
    background_name="background.jpg",     # 可 None
    zoom=105, x=50, y=46, speed=1.0,
)

# 查询动画：返回 [{"name": ..., "duration": ...}, ...]
anims = builder.query_animations(cli_path, "xxx.skel")

result = builder.build_wallpaper(
    cfg, "xxx.skel", "xxx.atlas", "xxx.png", "background.jpg",
    out_dir="输出目录", cli_path=cli_path,
    make_preview=True, make_zip=True,
)
```

CLI 调用时，若存在随包 `tools/dotnet/`，会自动把 `DOTNET_ROOT` 指向它并关闭全局多级查找，使用本地便携运行时。

## 八、重新打包（可选）

产物为 onedir 文件夹（资源约 95MB，不适合 onefile 单文件，否则每次启动都要解压）。在 Python 3.12 环境安装 PyInstaller 后，于源码目录执行（Windows 下 `--add-data` 分隔符为 `;`）：

```bash
pyinstaller --noconsole --name 壁纸生成器 \
  --add-data "template;template" \
  --add-data "tools;tools" \
  gui.py
```

产物在 `dist/壁纸生成器/`，整个文件夹压缩后分发。

> 本机 Python 3.12 禁用了 user site 目录，PyInstaller 若装在 `--user` 下，打包前需把其 site-packages 加入 `PYTHONPATH`；产物本身不依赖该环境。

## 九、限制与注意事项

- **三件套文件名不可重命名**：`.atlas` 内部记录的贴图名与 `.png` 强绑定，工具拷贝时保持原名。
- **运行时版本**：内置 Web 运行时与 CLI 均按 Spine 3.8 变体适配；若后续素材是其他 Spine 大版本（2.1 / 4.x），需替换 `template/spine-webgl-3.8.js`，并更换对应版本的 CLI 运行时 DLL 后验证解析。
- **未附带 ffmpeg**：随包 CLI 去掉了 103MB 的 ffmpeg.exe；查询动画、导出 PNG 预览不受影响，视频 / GIF 导出功能不可用。
- **预览图**：CLI 不可用或导出失败时，需手动放一张 16:9 的 `preview.png` 到工程根目录。
- **合规**：游戏解包素材仅限本人电脑私下使用，不要上传创意工坊、公开分享或商用；角色与立绘版权归游戏官方所有。
