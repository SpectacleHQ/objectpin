# ObjectPin

ObjectPin 是一个基于 PySide6 的桌面应用，用于在本地图片上运行
[NVIDIA LocateAnything-3B](https://huggingface.co/nvidia/LocateAnything-3B)。
它支持类别检测、短语定位、点选定位和文字检测，并会把模型返回的检测框或点位绘制回图片。

## 环境要求

- Windows
- Python 3.12 或更高版本
- [uv](https://docs.astral.sh/uv/)
- Intel XPU、NVIDIA CUDA，或 CPU 回退运行环境
- 支持 submodule 的 Git

项目当前在 `pyproject.toml` 中固定使用来自 PyTorch XPU 索引的
`torch==2.9.1+xpu` 和 `torchvision==0.24.1+xpu`。如果需要 CUDA 或 CPU
版本的 PyTorch，请先调整 `pyproject.toml`，再重新生成锁文件。

## 项目结构

```text
objectpin/
├─ src/objectpin/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ ui_main_window.py
│  └─ resources/
│     └─ main_window.ui
├─ models/
│  └─ LocateAnything-3B/        # Git submodule
├─ pyproject.toml
├─ uv.lock
└─ README.md
```

关键文件：

- `src/objectpin/main.py`：应用逻辑、模型加载、推理线程和 Qt 主窗口控制器。
- `src/objectpin/ui_main_window.py`：由 Qt Designer UI 文件生成的 PySide6 模块。
- `src/objectpin/resources/main_window.ui`：Qt Designer 源文件。
- `models/LocateAnything-3B`：指向
  `https://huggingface.co/nvidia/LocateAnything-3B` 的 Git submodule。

## 安装

克隆仓库时同时拉取 submodule：

```powershell
git clone --recurse-submodules <repo-url>
cd objectpin
```

如果已经克隆了仓库，初始化或更新模型 submodule：

```powershell
git submodule update --init --recursive
```

安装依赖：

```powershell
uv sync
```

## 运行

启动应用：

```powershell
uv run objectpin
```

也可以直接按模块运行：

```powershell
uv run python -m objectpin.main
```

## 模型 Submodule

模型以 Git submodule 形式管理，而不是直接提交到主仓库。这样可以避免主仓库体积过大，同时保留可复现的模型版本引用。

查看当前模型版本：

```powershell
git submodule status
```

更新到仓库记录的模型版本：

```powershell
git submodule update --init --recursive
```

如果需要主动升级到 Hugging Face 上游的新提交：

```powershell
git -C models/LocateAnything-3B fetch
git -C models/LocateAnything-3B checkout main
git -C models/LocateAnything-3B pull
git add models/LocateAnything-3B
```

## 开发

编译检查 Python 文件：

```powershell
python -m py_compile src/objectpin/main.py src/objectpin/ui_main_window.py src/objectpin/__init__.py
```

验证包导入和模型路径：

```powershell
uv run python -c "from objectpin.main import MODEL_PATH; print(MODEL_PATH); assert MODEL_PATH.exists()"
```

修改 Qt Designer 文件后，重新生成 Python UI 模块：

```powershell
uv run pyside6-uic src/objectpin/resources/main_window.ui -o src/objectpin/ui_main_window.py
```

修改依赖或构建元数据后，同步锁文件：

```powershell
uv lock
uv lock --check
```

## 常见问题

如果应用找不到模型，请先确认 submodule 已拉取：

```powershell
Test-Path models/LocateAnything-3B/config.json
git submodule status
```

如果依赖解析在非 Windows 平台失败，请检查 `pyproject.toml` 中 XPU 版本 PyTorch 的固定依赖。

如果修改 `.ui` 文件后界面没有变化，请从
`src/objectpin/resources/main_window.ui` 重新生成
`src/objectpin/ui_main_window.py`。
