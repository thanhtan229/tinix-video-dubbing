# -*- coding: utf-8 -*-
import cv2
from typing import Tuple, Optional
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QBrush, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QSlider, QDoubleSpinBox, QGroupBox, QMessageBox
)
from videotrans.configure.config import tr


class CropCanvas(QLabel):
    """Interactive canvas to view video frame and drag/draw subtitle ROI."""
    cropChanged = Signal(float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 360)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #0E1318; border: 1px solid #384956; border-radius: 6px;")
        self.pixmap_orig: Optional[QPixmap] = None

        # Normalized ratios (0.0 to 1.0): ymin, ymax, xmin, xmax
        self.ymin = 0.75
        self.ymax = 0.96
        self.xmin = 0.05
        self.xmax = 0.95

        self.dragging = False
        self.drag_mode = None  # 'new', 'move', 'top', 'bottom', 'left', 'right'
        self.drag_start = QPointF()

    def set_frame_image(self, q_image: QImage):
        self.pixmap_orig = QPixmap.fromImage(q_image)
        self.update()

    def set_ratios(self, ymin: float, ymax: float, xmin: float, xmax: float):
        self.ymin = max(0.0, min(1.0, ymin))
        self.ymax = max(0.0, min(1.0, ymax))
        self.xmin = max(0.0, min(1.0, xmin))
        self.xmax = max(0.0, min(1.0, xmax))
        self.update()
        self.cropChanged.emit(self.ymin, self.ymax, self.xmin, self.xmax)

    def get_display_rect(self) -> QRectF:
        if not self.pixmap_orig or self.pixmap_orig.isNull():
            return QRectF(0, 0, self.width(), self.height())
        scaled = self.pixmap_orig.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (self.width() - scaled.width()) / 2.0
        y = (self.height() - scaled.height()) / 2.0
        return QRectF(x, y, scaled.width(), scaled.height())

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        disp_rect = self.get_display_rect()

        if self.pixmap_orig and not self.pixmap_orig.isNull():
            scaled = self.pixmap_orig.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(int(disp_rect.x()), int(disp_rect.y()), scaled)

        # Calculate ROI box in screen coords
        box_x = disp_rect.x() + self.xmin * disp_rect.width()
        box_y = disp_rect.y() + self.ymin * disp_rect.height()
        box_w = (self.xmax - self.xmin) * disp_rect.width()
        box_h = (self.ymax - self.ymin) * disp_rect.height()
        roi_rect = QRectF(box_x, box_y, box_w, box_h)

        # Draw semi-transparent overlay outside ROI
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 130)))
        # Top
        painter.drawRect(QRectF(disp_rect.x(), disp_rect.y(), disp_rect.width(), box_y - disp_rect.y()))
        # Bottom
        painter.drawRect(QRectF(disp_rect.x(), box_y + box_h, disp_rect.width(), disp_rect.bottom() - (box_y + box_h)))
        # Left
        painter.drawRect(QRectF(disp_rect.x(), box_y, box_x - disp_rect.x(), box_h))
        # Right
        painter.drawRect(QRectF(box_x + box_w, box_y, disp_rect.right() - (box_x + box_w), box_h))

        # Draw Orange Selection Border
        pen = QPen(QColor("#FF4800"), 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 72, 0, 30)))
        painter.drawRect(roi_rect)

        # Draw label
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(int(box_x + 8), int(box_y + 18), tr("Subtitle Area (Vùng quét OCR)"))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            disp_rect = self.get_display_rect()
            pos = event.position()
            if disp_rect.contains(pos):
                self.dragging = True
                rx = (pos.x() - disp_rect.x()) / disp_rect.width()
                ry = (pos.y() - disp_rect.y()) / disp_rect.height()
                self.drag_start = QPointF(rx, ry)
                self.ymin = ry
                self.ymax = ry
                self.xmin = rx
                self.xmax = rx
                self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            disp_rect = self.get_display_rect()
            pos = event.position()
            rx = max(0.0, min(1.0, (pos.x() - disp_rect.x()) / disp_rect.width()))
            ry = max(0.0, min(1.0, (pos.y() - disp_rect.y()) / disp_rect.height()))

            self.xmin = min(self.drag_start.x(), rx)
            self.xmax = max(self.drag_start.x(), rx)
            self.ymin = min(self.drag_start.y(), ry)
            self.ymax = max(self.drag_start.y(), ry)

            self.update()
            self.cropChanged.emit(self.ymin, self.ymax, self.xmin, self.xmax)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            # Prevent zero size
            if abs(self.xmax - self.xmin) < 0.02:
                self.xmin = max(0.0, self.xmin - 0.1)
                self.xmax = min(1.0, self.xmax + 0.1)
            if abs(self.ymax - self.ymin) < 0.02:
                self.ymin = max(0.0, self.ymin - 0.05)
                self.ymax = min(1.0, self.ymax + 0.05)
            self.update()
            self.cropChanged.emit(self.ymin, self.ymax, self.xmin, self.xmax)


class CropSubtitleDialog(QDialog):
    """Dialog to visually choose subtitle crop area on video frame."""

    def __init__(self, video_path: str, current_box: Tuple[float, float, float, float] = (0.75, 0.96, 0.05, 0.95), parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Select Subtitle Area (Chọn vùng phụ đề)"))
        self.resize(800, 560)
        self.video_path = video_path
        self.selected_box = current_box

        layout = QVBoxLayout(self)

        info_label = QLabel(tr("Hướng dẫn: Kéo chuột trên khung hình để vẽ vùng chứa phụ đề cần nhận diện OCR."))
        info_label.setStyleSheet("color: #CAEBFF; font-weight: 500; margin-bottom: 4px;")
        layout.addWidget(info_label)

        self.canvas = CropCanvas(self)
        layout.addWidget(self.canvas, stretch=1)

        # Controls
        ctrl_group = QGroupBox(tr("Thông số vùng quét (Tỉ lệ %)"))
        ctrl_layout = QHBoxLayout(ctrl_group)

        self.spin_ymin = QDoubleSpinBox()
        self.spin_ymin.setRange(0, 100)
        self.spin_ymin.setSuffix(" %")

        self.spin_ymax = QDoubleSpinBox()
        self.spin_ymax.setRange(0, 100)
        self.spin_ymax.setSuffix(" %")

        self.spin_xmin = QDoubleSpinBox()
        self.spin_xmin.setRange(0, 100)
        self.spin_xmin.setSuffix(" %")

        self.spin_xmax = QDoubleSpinBox()
        self.spin_xmax.setRange(0, 100)
        self.spin_xmax.setSuffix(" %")

        ctrl_layout.addWidget(QLabel(tr("Trên (Y-Min):")))
        ctrl_layout.addWidget(self.spin_ymin)
        ctrl_layout.addWidget(QLabel(tr("Dưới (Y-Max):")))
        ctrl_layout.addWidget(self.spin_ymax)
        ctrl_layout.addWidget(QLabel(tr("Trái (X-Min):")))
        ctrl_layout.addWidget(self.spin_xmin)
        ctrl_layout.addWidget(QLabel(tr("Phải (X-Max):")))
        ctrl_layout.addWidget(self.spin_xmax)

        layout.addWidget(ctrl_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_reset = QPushButton(tr("Đặt lại vùng chuẩn (Đáy 20%)"))
        self.btn_reset.clicked.connect(self.reset_default)

        self.btn_ok = QPushButton(tr("Xác nhận"))
        self.btn_ok.setProperty("primary", True)
        self.btn_ok.clicked.connect(self.accept)

        self.btn_cancel = QPushButton(tr("Hủy bỏ"))
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

        # Connect signals
        self.canvas.cropChanged.connect(self.on_canvas_crop_changed)
        self.spin_ymin.valueChanged.connect(self.on_spin_changed)
        self.spin_ymax.valueChanged.connect(self.on_spin_changed)
        self.spin_xmin.valueChanged.connect(self.on_spin_changed)
        self.spin_xmax.valueChanged.connect(self.on_spin_changed)

        # Initialize
        ymin, ymax, xmin, xmax = current_box
        self.canvas.set_ratios(ymin, ymax, xmin, xmax)
        self.load_frame()

    def load_frame(self):
        if not self.video_path:
            return
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # Pick sample frame around 20%
        target_frame = max(0, int(total_frames * 0.20))
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.canvas.set_frame_image(q_img)

    def on_canvas_crop_changed(self, ymin, ymax, xmin, xmax):
        self.spin_ymin.blockSignals(True)
        self.spin_ymax.blockSignals(True)
        self.spin_xmin.blockSignals(True)
        self.spin_xmax.blockSignals(True)

        self.spin_ymin.setValue(ymin * 100.0)
        self.spin_ymax.setValue(ymax * 100.0)
        self.spin_xmin.setValue(xmin * 100.0)
        self.spin_xmax.setValue(xmax * 100.0)

        self.spin_ymin.blockSignals(False)
        self.spin_ymax.blockSignals(False)
        self.spin_xmin.blockSignals(False)
        self.spin_xmax.blockSignals(False)

        self.selected_box = (ymin, ymax, xmin, xmax)

    def on_spin_changed(self):
        ymin = self.spin_ymin.value() / 100.0
        ymax = self.spin_ymax.value() / 100.0
        xmin = self.spin_xmin.value() / 100.0
        xmax = self.spin_xmax.value() / 100.0
        self.selected_box = (ymin, ymax, xmin, xmax)
        self.canvas.set_ratios(ymin, ymax, xmin, xmax)

    def reset_default(self):
        self.canvas.set_ratios(0.75, 0.96, 0.05, 0.95)

    def get_crop_box(self) -> Tuple[float, float, float, float]:
        return self.selected_box
