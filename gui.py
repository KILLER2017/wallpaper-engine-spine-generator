# -*- coding: utf-8 -*-
"""
WE Web 壁纸生成器 · 桌面 GUI（tkinter）。

用带完整 Tcl/Tk 的 Python 3.12 运行：
    "D:\\Program Files\\Python312\\python.exe" gui.py
构建逻辑复用 builder.py；本文件只负责桌面界面与后台线程调度。
"""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import builder  # noqa: E402

DEFAULT_CLI = builder.find_cli()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("WE Web 壁纸生成器 · Spine")
        root.geometry("780x740")
        root.minsize(740, 680)

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.animations = []

        self._build_ui()
        self._poll_log()

        if DEFAULT_CLI:
            self._log("· 已自动定位 CLI：" + DEFAULT_CLI)
        else:
            self._log("⚠ 未自动找到 SpineViewerCLI，请点顶部“浏览…”手动选择。")

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        cli = ttk.LabelFrame(self.root, text="SpineViewer CLI（查询动画 / 导出预览帧，可选）")
        cli.pack(fill="x", **pad)
        self.cli_var = tk.StringVar(value=DEFAULT_CLI)
        ttk.Entry(cli, textvariable=self.cli_var).pack(side="left", fill="x", expand=True, padx=8, pady=6)
        ttk.Button(cli, text="浏览…", command=self._pick_cli).pack(side="left", padx=8)

        src = ttk.LabelFrame(self.root, text="Spine 三件套（.skel / .atlas / .png，文件名保持原名）")
        src.pack(fill="x", **pad)
        self.skel_var = tk.StringVar()
        self.atlas_var = tk.StringVar()
        self.png_var = tk.StringVar()
        self.bg_var = tk.StringVar()
        self._file_row(src, "骨骼 skel", self.skel_var, [("Skel", "*.skel")], self._on_skel_picked)
        self._file_row(src, "图集 atlas", self.atlas_var, [("Atlas", "*.atlas")], None)
        self._file_row(src, "贴图 png", self.png_var, [("PNG", "*.png")], None)
        self._file_row(src, "背景图（可选）", self.bg_var, [("图片", "*.jpg *.jpeg *.png")], None)

        anim = ttk.LabelFrame(self.root, text="动画（点“查询动画”自动读取）")
        anim.pack(fill="x", **pad)
        top = ttk.Frame(anim)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="主动画（循环）").pack(side="left")
        self.anim_var = tk.StringVar()
        self.anim_combo = ttk.Combobox(top, textvariable=self.anim_var, width=26, state="readonly")
        self.anim_combo.pack(side="left", padx=8)
        ttk.Button(top, text="查询动画", command=self._query).pack(side="left", padx=8)

        ttk.Label(anim, text="表情 / 姿势切片（时长 0，勾选后在 WE 面板下拉切换；可不选）").pack(anchor="w", padx=8)
        list_row = ttk.Frame(anim)
        list_row.pack(fill="x", padx=8, pady=(0, 6))
        self.expr_list = tk.Listbox(list_row, selectmode="multiple", height=5, exportselection=False)
        self.expr_list.pack(side="left", fill="x", expand=True)
        sb = ttk.Scrollbar(list_row, orient="vertical", command=self.expr_list.yview)
        sb.pack(side="right", fill="y")
        self.expr_list.config(yscrollcommand=sb.set)

        prop = ttk.LabelFrame(self.root, text="壁纸默认属性（导入 WE 后仍可实时调整）")
        prop.pack(fill="x", **pad)
        self.title_var = tk.StringVar(value="角色-壁纸")
        self.zoom_var = tk.StringVar(value="105")
        self.speed_var = tk.StringVar(value="1")
        self.align_h_var = tk.StringVar(value="center")
        self.align_v_var = tk.StringVar(value="center")
        self.x_var = tk.StringVar(value="50")
        self.y_var = tk.StringVar(value="46")

        ttk.Label(prop, text="标题").grid(row=0, column=0, padx=8, pady=6, sticky="w")
        ttk.Entry(prop, textvariable=self.title_var, width=38).grid(row=0, column=1, columnspan=3, padx=8, sticky="we")

        ttk.Label(prop, text="缩放 %").grid(row=1, column=0, padx=8, pady=6, sticky="w")
        ttk.Spinbox(prop, from_=50, to=200, textvariable=self.zoom_var, width=8).grid(row=1, column=1, padx=8, sticky="w")
        ttk.Label(prop, text="速度倍速").grid(row=1, column=2, padx=8, pady=6, sticky="w")
        ttk.Spinbox(prop, from_=0.2, to=2, increment=0.05, textvariable=self.speed_var, width=8).grid(row=1, column=3, padx=8, sticky="w")

        ttk.Label(prop, text="水平对齐").grid(row=2, column=0, padx=8, pady=6, sticky="w")
        ttk.Combobox(prop, textvariable=self.align_h_var, width=8, state="readonly",
                     values=["left", "center", "right"]).grid(row=2, column=1, padx=8, sticky="w")
        ttk.Label(prop, text="垂直对齐").grid(row=2, column=2, padx=8, pady=6, sticky="w")
        ttk.Combobox(prop, textvariable=self.align_v_var, width=8, state="readonly",
                     values=["top", "center", "bottom"]).grid(row=2, column=3, padx=8, sticky="w")

        ttk.Label(prop, text="水平位置 %").grid(row=3, column=0, padx=8, pady=6, sticky="w")
        ttk.Spinbox(prop, from_=0, to=100, textvariable=self.x_var, width=8).grid(row=3, column=1, padx=8, sticky="w")
        ttk.Label(prop, text="垂直位置 %").grid(row=3, column=2, padx=8, pady=6, sticky="w")
        ttk.Spinbox(prop, from_=0, to=100, textvariable=self.y_var, width=8).grid(row=3, column=3, padx=8, sticky="w")
        prop.columnconfigure(1, weight=1)

        out = ttk.LabelFrame(self.root, text="输出")
        out.pack(fill="x", **pad)
        self.outdir_var = tk.StringVar()
        ttk.Entry(out, textvariable=self.outdir_var).pack(side="left", fill="x", expand=True, padx=8, pady=6)
        ttk.Button(out, text="选择目录…", command=self._pick_outdir).pack(side="left", padx=8)

        opt = ttk.Frame(out)
        opt.pack(fill="x", padx=8, pady=(0, 6))
        self.preview_var = tk.BooleanVar(value=True)
        self.zip_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text="CLI 导出预览帧 preview.png", variable=self.preview_var).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(opt, text="同时打包 zip（平铺结构）", variable=self.zip_var).pack(side="left")

        btn = ttk.Frame(self.root)
        btn.pack(fill="x", **pad)
        self.run_btn = ttk.Button(btn, text="生成壁纸", command=self._build)
        self.run_btn.pack(side="right")

        log_frame = ttk.LabelFrame(self.root, text="日志")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=6)

    def _file_row(self, parent, label, var, filetypes, on_pick):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=8, pady=3)
        ttk.Label(row, text=label, width=14).pack(side="left")
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="浏览…", command=lambda: self._pick_file(var, filetypes, on_pick)).pack(side="left")

    # ---------------------------------------------------------------- helpers
    def _pick_cli(self):
        p = filedialog.askopenfilename(title="选择 SpineViewerCLI.exe", filetypes=[("EXE", "*.exe")])
        if p:
            self.cli_var.set(p)

    def _pick_file(self, var, filetypes, on_pick):
        p = filedialog.askopenfilename(title="选择文件", filetypes=filetypes)
        if p:
            var.set(p)
            if on_pick:
                on_pick(p)

    def _pick_outdir(self):
        p = filedialog.askdirectory(title="选择输出目录")
        if p:
            self.outdir_var.set(p)

    def _on_skel_picked(self, skel: str):
        base = os.path.splitext(skel)[0]
        if not self.atlas_var.get():
            self.atlas_var.set(base + ".atlas")
        if not self.png_var.get():
            self.png_var.set(base + ".png")

    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _poll_log(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(100, self._poll_log)

    # ---------------------------------------------------------------- actions
    def _query(self):
        skel = self.skel_var.get().strip()
        if not skel:
            messagebox.showwarning("提示", "请先选择 .skel 文件。")
            return
        cli = self.cli_var.get().strip()
        if not cli or not os.path.exists(cli):
            messagebox.showwarning("未找到 CLI", "请先在顶部浏览选择 SpineViewerCLI.exe。")
            self._log("✗ 未找到 SpineViewerCLI：" + (cli or "（未选择）"))
            return
        try:
            self._log("· 读取动画列表…")
            self.animations = builder.query_animations(cli, skel)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("查询失败", str(e))
            self._log("✗ 查询失败：" + str(e))
            return

        loops = [a["name"] for a in self.animations if a["duration"] > 0]
        exprs = [a["name"] for a in self.animations if a["duration"] <= 0]
        self.anim_combo["values"] = loops
        if loops:
            self.anim_var.set(loops[0])
        self.expr_list.delete(0, "end")
        for e in exprs:
            self.expr_list.insert("end", e)
        self.expr_list.selection_set(0, "end")
        self._log("· 主动画：" + (", ".join(loops) or "无"))
        self._log("· 表情切片：" + (", ".join(exprs) or "无"))

    def _selected_exprs(self):
        return [self.expr_list.get(i) for i in self.expr_list.curselection()]

    def _build(self):
        skel = self.skel_var.get().strip()
        atlas = self.atlas_var.get().strip()
        png = self.png_var.get().strip()
        bg = self.bg_var.get().strip() or None
        outdir = self.outdir_var.get().strip()
        anim = self.anim_var.get().strip()

        if not (skel and atlas and png and outdir and anim):
            messagebox.showwarning("提示", "请补齐三件套、主动画与输出目录。")
            return
        if not (os.path.exists(skel) and os.path.exists(atlas) and os.path.exists(png)):
            messagebox.showerror("错误", "三件套源文件不存在，请检查路径。")
            return

        try:
            cfg = builder.WallpaperConfig(
                title=self.title_var.get().strip() or "壁纸",
                skel_name=os.path.basename(skel),
                atlas_name=os.path.basename(atlas),
                png_name=os.path.basename(png),
                anim=anim,
                expressions=self._selected_exprs(),
                background_name=os.path.basename(bg) if bg else None,
                zoom=int(float(self.zoom_var.get())),
                x=int(float(self.x_var.get())),
                y=int(float(self.y_var.get())),
                speed=float(self.speed_var.get()),
                align_h=self.align_h_var.get(),
                align_v=self.align_v_var.get(),
            )
        except ValueError as e:
            messagebox.showerror("参数错误", "数值填写有误：" + str(e))
            return

        self.run_btn.configure(state="disabled")
        self._log("=== 开始生成：" + cfg.title + " ===")
        threading.Thread(target=self._worker, args=(cfg, skel, atlas, png, bg, outdir),
                         daemon=True).start()

    def _worker(self, cfg, skel, atlas, png, bg, outdir):
        try:
            result = builder.build_wallpaper(
                cfg, skel, atlas, png, bg, outdir,
                cli_path=self.cli_var.get().strip(),
                make_preview=self.preview_var.get(),
                make_zip=self.zip_var.get(),
                log=self._log,
            )
            self._log("=== 完成 ===")
            self._log("工程目录：" + result["out_dir"])
            if result["zip"]:
                self._log("压缩包：" + result["zip"])
            for w in result["warnings"]:
                self._log("⚠ " + w)
            self.root.after(0, lambda: messagebox.showinfo("完成", "壁纸工程已生成。\n" + result["out_dir"]))
        except Exception as e:  # noqa: BLE001
            self._log("✗ 生成失败：" + str(e))
            self.root.after(0, lambda: messagebox.showerror("生成失败", str(e)))
        finally:
            self.root.after(0, lambda: self.run_btn.configure(state="normal"))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
