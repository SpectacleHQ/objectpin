from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict, cast

import torch
from PIL import Image, ImageDraw
from PySide6.QtCore import QThread, Qt, Signal, SignalInstance
from PySide6.QtGui import QColor, QCloseEvent, QImage, QPalette, QPixmap, QResizeEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox
from transformers import AutoModel, AutoProcessor, AutoTokenizer

from .ui_main_window import Ui_MainWindow

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "LocateAnything-3B"


class Box(TypedDict):
    """检测框坐标。

    坐标使用原图像素坐标，左上角为原点。

    :ivar x1: 左上角 x 坐标。
    :ivar y1: 左上角 y 坐标。
    :ivar x2: 右下角 x 坐标。
    :ivar y2: 右下角 y 坐标。
    """

    x1: float
    y1: float
    x2: float
    y2: float


class Point(TypedDict):
    """点位坐标。

    坐标使用原图像素坐标，左上角为原点。

    :ivar x: 点位 x 坐标。
    :ivar y: 点位 y 坐标。
    """

    x: float
    y: float


def choose_device() -> str:
    """选择当前可用的推理设备。

    优先使用 Intel XPU，其次使用 CUDA，最后回退到 CPU。

    :return: PyTorch 设备名称。
    """

    if hasattr(torch, "xpu") and torch.xpu.is_available():
        return "xpu"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def choose_dtype(device: str) -> torch.dtype:
    """根据设备选择默认推理精度。

    :param device: PyTorch 设备名称。
    :return: 适合该设备的张量精度。
    """

    if device.startswith("xpu"):
        return torch.bfloat16
    if device.startswith("cuda"):
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    return torch.float32


def resize_keep_aspect(image: Image.Image, max_side: int) -> tuple[Image.Image, float, float]:
    """按比例缩小图像并返回回映射比例。

    只在图像最长边超过 ``max_side`` 时缩小，不会放大图像。返回的
    ``scale_x`` 和 ``scale_y`` 用于把缩小图上的推理结果映射回原图。

    :param image: 原始 RGB 图像。
    :param max_side: 推理图像允许的最长边。
    :return: ``(缩小图, x 方向回映射比例, y 方向回映射比例)``。
    """

    width, height = image.size
    scale = min(1.0, max_side / max(width, height))
    if scale == 1.0:
        return image.copy(), 1.0, 1.0

    resized_width = max(1, round(width * scale))
    resized_height = max(1, round(height * scale))
    resized = image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
    return resized, width / resized_width, height / resized_height


def synchronize_device(device: str) -> None:
    """同步异步 GPU/XPU 队列。

    PyTorch 的 GPU/XPU 操作通常是异步的，推理计时和结果读取前需要显式同步。

    :param device: PyTorch 设备名称。
    :return: 无返回值。
    """

    if device.startswith("xpu") and hasattr(torch, "xpu") and torch.xpu.is_available():
        torch.xpu.synchronize()
    elif device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.synchronize()


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    """把 PIL 图像转换为 Qt 可显示的 ``QPixmap``。

    :param image: PIL 图像。
    :return: 可直接设置到 ``QLabel`` 的 Qt 位图。
    """

    rgba = image.convert("RGBA")
    width, height = rgba.size
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, width, height, width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


def draw_results(image: Image.Image, boxes: list[Box], points: list[Point]) -> Image.Image:
    """在原图上绘制检测框和点位。

    :param image: 原始 RGB 图像。
    :param boxes: 已映射回原图坐标系的检测框列表。
    :param points: 已映射回原图坐标系的点位列表。
    :return: 绘制完成的新图像。
    """

    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    width, height = image.size
    line_width = max(3, round(max(width, height) / 320))
    point_radius = max(6, round(max(width, height) / 160))

    for index, box in enumerate(boxes, start=1):
        x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
        draw.rectangle((x1, y1, x2, y2), outline="#ff3b30", width=line_width)
        label = str(index)
        label_box = draw.textbbox((0, 0), label)
        label_width = label_box[2] - label_box[0] + 12
        label_height = label_box[3] - label_box[1] + 8
        draw.rectangle((x1, max(0, y1 - label_height), x1 + label_width, y1), fill="#ff3b30")
        draw.text((x1 + 6, max(0, y1 - label_height + 3)), label, fill="white")

    for point in points:
        x, y = point["x"], point["y"]
        draw.ellipse(
            (x - point_radius, y - point_radius, x + point_radius, y + point_radius),
            outline="#007aff",
            width=line_width,
        )
        draw.line((x - point_radius, y, x + point_radius, y), fill="#007aff", width=line_width)
        draw.line((x, y - point_radius, x, y + point_radius), fill="#007aff", width=line_width)

    return annotated


def split_categories(text: str) -> list[str]:
    """切分用户输入的类别列表。

    支持英文逗号、英文分号、中文逗号、中文分号和换行。

    :param text: 类别输入文本。
    :return: 去掉空白后的类别名称列表。
    """

    return [item.strip() for item in re.split(r"[,;，；\n]+", text) if item.strip()]


class LocateAnythingWorker:
    """LocateAnything 常驻推理工作器。

    该类负责一次性加载 tokenizer、processor 和模型权重，之后复用同一个模型实例
    服务 GUI 中的多次推理请求，避免每次点击按钮都重新加载模型。
    """

    def __init__(
            self,
            model_path: str | Path,
            device: str | None = None,
            dtype: torch.dtype | None = None,
    ) -> None:
        """初始化并加载模型。

        :param model_path: 本地模型目录或 Hugging Face 模型名称。
        :param device: 指定推理设备；为 ``None`` 时自动选择。
        :param dtype: 指定推理精度；为 ``None`` 时根据设备自动选择。
        :return: 无返回值。
        """

        self.device = device or choose_device()
        self.dtype = dtype or choose_dtype(self.device)
        model_path = str(model_path)

        # 模型加载只发生一次，后续推理复用 self.model。
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        model = AutoModel.from_pretrained(
            model_path,
            torch_dtype=self.dtype,
            trust_remote_code=True,
        )
        self.model = model.to(self.device).eval()
        synchronize_device(self.device)

    @torch.no_grad()
    def predict(
            self,
            image: Image.Image,
            question: str,
            generation_mode: str = "fast",
            max_new_tokens: int = 256,
            temperature: float = 1.0,
            do_sample: bool = False,
            verbose: bool = True,
    ) -> dict[str, Any]:
        """执行一次通用视觉语言推理。

        :param image: 送入模型的 RGB 图像，通常已经按比例缩小。
        :param question: 发送给模型的自然语言 prompt。
        :param generation_mode: 官方生成模式，支持 ``fast``、``hybrid``、``slow``。
        :param max_new_tokens: 生成结果允许的最大 token 数。
        :param temperature: 生成温度；非采样模式下保留默认值即可。
        :param do_sample: 是否启用采样。
        :param verbose: 是否打印模型内部统计信息。
        :return: 包含 ``answer`` 以及可选 ``history``、``stats`` 的字典。
        """

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": question},
                ],
            }
        ]

        text = self.processor.py_apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        images, videos = self.processor.process_vision_info(messages)
        inputs = self.processor(
            text=[text], images=images, videos=videos, return_tensors="pt"
        ).to(self.device)

        pixel_values = inputs["pixel_values"].to(self.dtype)
        input_ids = inputs["input_ids"]
        image_grid_hws = inputs.get("image_grid_hws", None)

        synchronize_device(self.device)
        response = self.model.generate(
            pixel_values=pixel_values,
            input_ids=input_ids,
            attention_mask=inputs["attention_mask"],
            image_grid_hws=image_grid_hws,
            tokenizer=self.tokenizer,
            max_new_tokens=max_new_tokens,
            use_cache=True,
            generation_mode=generation_mode,
            temperature=temperature,
            do_sample=do_sample,
            top_p=0.9,
            repetition_penalty=1.1,
            verbose=verbose,
        )
        synchronize_device(self.device)

        result = {"answer": response[0] if isinstance(response, tuple) else response}
        if isinstance(response, tuple) and len(response) >= 3:
            result["history"] = response[1]
            result["stats"] = response[2]
        return result

    def detect(self, image: Image.Image, categories: list[str], **kwargs: Any) -> dict[str, Any]:
        """检测一个或多个类别。

        :param image: 送入模型的 RGB 图像。
        :param categories: 类别名称列表。
        :param kwargs: 透传给 :meth:`predict` 的生成参数。
        :return: 模型推理结果。
        """

        cats = "</c>".join(categories)
        prompt = f"Locate all the instances that matches the following description: {cats}."
        return self.predict(image, prompt, **kwargs)

    def ground_multi(self, image: Image.Image, phrase: str, **kwargs: Any) -> dict[str, Any]:
        """根据短语定位多个匹配实例。

        :param image: 送入模型的 RGB 图像。
        :param phrase: 自然语言描述。
        :param kwargs: 透传给 :meth:`predict` 的生成参数。
        :return: 模型推理结果。
        """

        prompt = f"Locate all the instances that match the following description: {phrase}."
        return self.predict(image, prompt, **kwargs)

    def detect_text(self, image: Image.Image, **kwargs: Any) -> dict[str, Any]:
        """检测图像中的文字区域。

        :param image: 送入模型的 RGB 图像。
        :param kwargs: 透传给 :meth:`predict` 的生成参数。
        :return: 模型推理结果。
        """

        return self.predict(image, "Detect all the text in box format.", **kwargs)

    def point(self, image: Image.Image, phrase: str, **kwargs: Any) -> dict[str, Any]:
        """根据短语输出目标点位。

        :param image: 送入模型的 RGB 图像。
        :param phrase: 自然语言描述。
        :param kwargs: 透传给 :meth:`predict` 的生成参数。
        :return: 模型推理结果。
        """

        return self.predict(image, f"Point to: {phrase}.", **kwargs)

    @staticmethod
    def parse_boxes(answer: str, image_width: int, image_height: int) -> list[Box]:
        """从模型输出文本中解析检测框。

        模型输出坐标为 ``0`` 到 ``1000`` 的归一化整数，这里会转换为指定图像尺寸下的
        像素坐标。

        :param answer: 模型原始文本输出。
        :param image_width: 输出坐标对应图像的宽度。
        :param image_height: 输出坐标对应图像的高度。
        :return: 检测框列表。
        """

        boxes: list[Box] = []
        for match in re.finditer(r"<box><(\d+)><(\d+)><(\d+)><(\d+)></box>", answer):
            x1, y1, x2, y2 = [int(value) for value in match.groups()]
            boxes.append(
                {
                    "x1": x1 / 1000 * image_width,
                    "y1": y1 / 1000 * image_height,
                    "x2": x2 / 1000 * image_width,
                    "y2": y2 / 1000 * image_height,
                }
            )
        return boxes

    @staticmethod
    def parse_points(answer: str, image_width: int, image_height: int) -> list[Point]:
        """从模型输出文本中解析点位。

        模型输出坐标为 ``0`` 到 ``1000`` 的归一化整数，这里会转换为指定图像尺寸下的
        像素坐标。

        :param answer: 模型原始文本输出。
        :param image_width: 输出坐标对应图像的宽度。
        :param image_height: 输出坐标对应图像的高度。
        :return: 点位列表。
        """

        points: list[Point] = []
        for match in re.finditer(r"<box><(\d+)><(\d+)></box>", answer):
            x, y = int(match.group(1)), int(match.group(2))
            points.append({"x": x / 1000 * image_width, "y": y / 1000 * image_height})
        return points


@dataclass
class InferenceResult:
    """后台推理线程返回给主窗口的数据。

    :ivar answer: 模型原始文本输出。
    :ivar annotated_image: 已在原图坐标系绘制结果的新图像。
    :ivar boxes: 原图坐标系中的检测框列表。
    :ivar points: 原图坐标系中的点位列表。
    :ivar original_size: 原图尺寸。
    :ivar resized_size: 实际送入模型的缩小图尺寸。
    :ivar elapsed_seconds: 本次推理总耗时，单位为秒。
    """

    answer: str
    annotated_image: Image.Image
    boxes: list[Box]
    points: list[Point]
    original_size: tuple[int, int]
    resized_size: tuple[int, int]
    elapsed_seconds: float


class ModelLoadThread(QThread):
    """模型加载线程。

    GUI 启动后在后台加载模型，避免主线程被长时间阻塞。
    """

    loaded = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        """在线程中加载模型并发射结果信号。

        :return: 无返回值。
        """

        try:
            worker = LocateAnythingWorker(MODEL_PATH)
            self.loaded.emit(worker)
        except Exception as exc:
            self.failed.emit(str(exc))


class InferenceThread(QThread):
    """后台推理线程。

    该线程负责缩图、调用模型、解析输出、把结果坐标映射回原图并绘制标注图。
    """

    finished_result = Signal(object)
    failed = Signal(str)

    def __init__(
            self,
            worker: LocateAnythingWorker,
            image: Image.Image,
            task: str,
            query: str,
            max_side: int,
            generation_mode: str,
            max_new_tokens: int,
    ) -> None:
        """初始化一次推理任务。

        :param worker: 已经加载完成的模型工作器。
        :param image: 原始 RGB 图像。
        :param task: GUI 中选择的任务名称。
        :param query: 用户输入的查询文本。
        :param max_side: 推理前缩图的最长边。
        :param generation_mode: 官方生成模式。
        :param max_new_tokens: 最大生成 token 数。
        :return: 无返回值。
        """

        super().__init__()
        self.worker = worker
        self.image = image.copy()
        self.task = task
        self.query = query
        self.max_side = max_side
        self.generation_mode = generation_mode
        self.max_new_tokens = max_new_tokens

    def run(self) -> None:
        """执行后台推理任务。

        :return: 无返回值。
        """

        try:
            started_at = time.perf_counter()
            resized, scale_x, scale_y = resize_keep_aspect(self.image, self.max_side)
            result = self._run_task(resized)
            answer = str(result["answer"])

            # 先在缩小图坐标系解析，再按比例回映射到原图。
            resized_width, resized_height = resized.size
            boxes = LocateAnythingWorker.parse_boxes(answer, resized_width, resized_height)
            points = LocateAnythingWorker.parse_points(answer, resized_width, resized_height)
            scaled_boxes: list[Box] = [
                Box(
                    x1=box["x1"] * scale_x,
                    y1=box["y1"] * scale_y,
                    x2=box["x2"] * scale_x,
                    y2=box["y2"] * scale_y,
                )
                for box in boxes
            ]
            scaled_points: list[Point] = [
                Point(x=point["x"] * scale_x, y=point["y"] * scale_y)
                for point in points
            ]
            annotated = draw_results(self.image, scaled_boxes, scaled_points)

            self.finished_result.emit(
                InferenceResult(
                    answer=answer,
                    annotated_image=annotated,
                    boxes=scaled_boxes,
                    points=scaled_points,
                    original_size=self.image.size,
                    resized_size=resized.size,
                    elapsed_seconds=time.perf_counter() - started_at,
                )
            )
        except Exception as exc:
            self.failed.emit(str(exc))

    def _run_task(self, resized: Image.Image) -> dict[str, Any]:
        """按任务类型构造 prompt 并调用模型。

        :param resized: 已按比例缩小的 RGB 图像。
        :return: 模型推理结果。
        :raises ValueError: 当任务需要查询文本但用户未填写时抛出。
        """

        kwargs = {
            "generation_mode": self.generation_mode,
            "max_new_tokens": self.max_new_tokens,
        }
        if self.task == "Detect categories":
            categories = split_categories(self.query)
            if not categories:
                raise ValueError("Enter at least one category.")
            return self.worker.detect(resized, categories, **kwargs)
        if self.task == "Ground phrase":
            if not self.query.strip():
                raise ValueError("Enter a phrase.")
            return self.worker.ground_multi(resized, self.query.strip(), **kwargs)
        if self.task == "Point to phrase":
            if not self.query.strip():
                raise ValueError("Enter a phrase.")
            return self.worker.point(resized, self.query.strip(), **kwargs)
        return self.worker.detect_text(resized, **kwargs)


class MainWindow(QMainWindow):
    """ObjectPin 主窗口。

    主窗口负责组织 UI、管理后台线程、显示图像以及展示模型输出。
    """

    def __init__(self) -> None:
        """初始化主窗口并开始后台加载模型。

        :return: 无返回值。
        """

        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.worker: LocateAnythingWorker | None = None
        self.load_thread: ModelLoadThread | None = None
        self.inference_thread: InferenceThread | None = None
        self.original_image: Image.Image | None = None
        self.current_pixmap: QPixmap | None = None

        self._setup_styles()
        self._connect_signals()
        self._set_loading("Loading model...")
        self._start_model_load()

    def _setup_styles(self) -> None:
        """设置应用内固定浅色样式。

        该样式不跟随系统深色模式，避免深色模式下出现低对比度文字。

        :return: 无返回值。
        """

        self.ui.centralwidget.setStyleSheet("QWidget#centralwidget { background: #eef1f5; }")
        self.ui.imageFrame.setStyleSheet(
            "QFrame { background: #f7f8fa; border: 1px solid #d7dbe2; border-radius: 6px; }"
            "QLabel { color: #687384; font-size: 18px; }"
        )
        self.ui.controlPanel.setStyleSheet(
            "QFrame#controlPanel { background: #eef1f5; border: 0; }"
            "QLabel { color: #1f2937; font-size: 13px; font-weight: 500; }"
            "QLineEdit, QComboBox, QSpinBox, QTextEdit {"
            "  border: 1px solid #c7ced8; border-radius: 5px; padding: 6px;"
            "  background: #ffffff; color: #111827; selection-background-color: #1f6feb;"
            "  selection-color: #ffffff;"
            "}"
            "QComboBox QAbstractItemView { background: #ffffff; color: #111827;"
            "  selection-background-color: #1f6feb; selection-color: #ffffff; }"
            "QPushButton { background: #1f6feb; color: white; border: 0; border-radius: 5px;"
            "  padding: 8px 12px; font-weight: 600; }"
            "QPushButton:disabled { background: #b8c1cc; color: #ffffff; }"
            "QPushButton:hover:!disabled { background: #195fc7; }"
            "QProgressBar { border: 1px solid #cfd6df; border-radius: 4px; height: 8px;"
            "  background: #ffffff; }"
            "QProgressBar::chunk { background: #1f6feb; border-radius: 3px; }"
        )

    def _connect_signals(self) -> None:
        """连接 UI 控件和后台线程信号。

        显式连接 UI 控件信号，避免依赖 ``QMetaObject.connectSlotsByName`` 在
        Python 方法上的自动连接行为。

        :return: 无返回值。
        """

        self.ui.openButton.clicked.connect(self.on_openButton_clicked)
        self.ui.runButton.clicked.connect(self.on_runButton_clicked)
        self.ui.taskCombo.currentTextChanged.connect(self.on_taskCombo_currentTextChanged)

    def _start_model_load(self) -> None:
        """启动后台模型加载线程。

        :return: 无返回值。
        """

        load_thread = ModelLoadThread()
        cast(SignalInstance, load_thread.loaded).connect(self.on_loadThread_loaded)
        cast(SignalInstance, load_thread.failed).connect(self.on_loadThread_failed)
        self.load_thread = load_thread
        load_thread.start()

    def on_loadThread_loaded(self, worker: LocateAnythingWorker) -> None:
        """处理模型加载成功信号。

        :param worker: 已加载完成的模型工作器。
        :return: 无返回值。
        """

        self.worker = worker
        self._set_busy(False, f"Model ready on {worker.device}; open an image.")
        self._refresh_run_enabled()

    def on_loadThread_failed(self, message: str) -> None:
        """处理模型加载失败信号。

        :param message: 异常消息。
        :return: 无返回值。
        """

        self._set_busy(False, "Model load failed.")
        QMessageBox.critical(self, "Model load failed", message)

    def on_openButton_clicked(self, checked: bool = False) -> None:
        """处理打开图片按钮点击信号。

        :param checked: 按钮选中状态；普通按钮会传入 ``False``。
        :return: 无返回值。
        """

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All files (*.*)",
        )
        if not path:
            return

        try:
            original_image = Image.open(path).convert("RGB")
        except Exception as exc:
            QMessageBox.warning(self, "Open image failed", str(exc))
            return

        self.original_image = original_image
        self._show_image(original_image)
        width, height = original_image.size
        self.ui.statusLabel.setText(f"Image loaded: {width}x{height}")
        self.ui.outputEdit.clear()
        self._refresh_run_enabled()

    def on_runButton_clicked(self, checked: bool = False) -> None:
        """处理运行推理按钮点击信号。

        :param checked: 按钮选中状态；普通按钮会传入 ``False``。
        :return: 无返回值。
        """

        if self.worker is None or self.original_image is None:
            return

        worker = self.worker
        original_image = self.original_image
        self._set_busy(True, "Running inference...")
        inference_thread = InferenceThread(
            worker=worker,
            image=original_image,
            task=self.ui.taskCombo.currentText(),
            query=self.ui.queryEdit.text(),
            max_side=self.ui.maxSideSpin.value(),
            generation_mode=self.ui.modeCombo.currentText(),
            max_new_tokens=self.ui.tokensSpin.value(),
        )
        inference_thread.finished_result.connect(
            self.on_inferenceThread_finished_result
        )
        inference_thread.failed.connect(self.on_inferenceThread_failed)
        self.inference_thread = inference_thread
        inference_thread.start()

    def on_inferenceThread_finished_result(self, result: InferenceResult) -> None:
        """处理推理成功信号。

        :param result: 后台推理线程返回的结果对象。
        :return: 无返回值。
        """

        self._set_busy(False, "Inference complete.")
        self._show_image(result.annotated_image)
        self.ui.statusLabel.setText(
            "Done in "
            f"{result.elapsed_seconds:.1f}s | original {result.original_size[0]}x{result.original_size[1]} "
            f"| inference {result.resized_size[0]}x{result.resized_size[1]} "
            f"| boxes {len(result.boxes)} | points {len(result.points)}"
        )
        self.ui.outputEdit.setPlainText(result.answer)
        self._refresh_run_enabled()

    def on_inferenceThread_failed(self, message: str) -> None:
        """处理推理失败信号。

        :param message: 异常消息。
        :return: 无返回值。
        """

        self._set_busy(False, "Inference failed.")
        self._refresh_run_enabled()
        QMessageBox.warning(self, "Inference failed", message)

    def on_taskCombo_currentTextChanged(self, task: str) -> None:
        """处理任务类型切换信号。

        根据任务类型启用或禁用查询输入框，并在合适时填入默认类别。

        :param task: 当前任务名称。
        :return: 无返回值。
        """

        if task == "Detect categories":
            self.ui.queryEdit.setEnabled(True)
            if not self.ui.queryEdit.text().strip():
                self.ui.queryEdit.setText("car")
        elif task == "Detect text":
            self.ui.queryEdit.setEnabled(False)
        else:
            self.ui.queryEdit.setEnabled(True)
            if self.ui.queryEdit.text().strip() == "car":
                self.ui.queryEdit.clear()

    def _set_busy(self, busy: bool, status: str) -> None:
        """切换运行中状态。

        :param busy: 是否正在执行会阻塞按钮的任务。
        :param status: 展示在状态栏中的文本。
        :return: 无返回值。
        """

        self.ui.progressBar.setRange(0, 0 if busy else 1)
        self.ui.progressBar.setValue(0 if busy else 1)
        self.ui.statusLabel.setText(status)
        self.ui.openButton.setEnabled(not busy)
        self.ui.runButton.setEnabled(False if busy else self.worker is not None and self.original_image is not None)

    def _set_loading(self, status: str) -> None:
        """切换模型加载状态。

        模型加载时允许先打开图片，但禁用运行按钮。

        :param status: 展示在状态栏中的文本。
        :return: 无返回值。
        """

        self.ui.progressBar.setRange(0, 0)
        self.ui.progressBar.setValue(0)
        self.ui.statusLabel.setText(status)
        self.ui.openButton.setEnabled(True)
        self.ui.runButton.setEnabled(False)

    def _refresh_run_enabled(self) -> None:
        """根据模型、图片和线程状态刷新运行按钮。

        :return: 无返回值。
        """

        is_running = self.inference_thread is not None and self.inference_thread.isRunning()
        self.ui.runButton.setEnabled(self.worker is not None and self.original_image is not None and not is_running)

    def _show_image(self, image: Image.Image) -> None:
        """在主预览区显示图像。

        :param image: 要显示的 PIL 图像。
        :return: 无返回值。
        """

        self.current_pixmap = pil_to_pixmap(image)
        self._fit_current_pixmap()

    def _fit_current_pixmap(self) -> None:
        """按预览区尺寸等比例缩放当前图像。

        :return: 无返回值。
        """

        if self.current_pixmap is None:
            return
        target = self.ui.imageLabel.size()
        scaled = self.current_pixmap.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.ui.imageLabel.setPixmap(scaled)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """处理窗口尺寸变化事件。

        :param event: Qt 尺寸变化事件。
        :return: 无返回值。
        """

        super().resizeEvent(event)
        self._fit_current_pixmap()

    def closeEvent(self, event: QCloseEvent) -> None:
        """处理窗口关闭事件。

        后台线程仍在运行时阻止关闭，避免 Qt 在线程未结束时销毁对象。

        :param event: Qt 关闭事件。
        :return: 无返回值。
        """

        load_running = self.load_thread is not None and self.load_thread.isRunning()
        infer_running = self.inference_thread is not None and self.inference_thread.isRunning()
        if load_running or infer_running:
            QMessageBox.information(self, "Busy", "A model task is still running. Close after it finishes.")
            event.ignore()
            return
        event.accept()


def main() -> int:
    """创建并运行 Qt 应用。

    :return: Qt 应用退出码。
    """

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#eef1f5"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f7f8fa"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1f6feb"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#111827"))
    app.setPalette(palette)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
