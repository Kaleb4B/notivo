import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QLinearGradient
from PySide6.QtCore import Qt, QTimer
import math

class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.history_size = 80
        self.levels = [0.0] * self.history_size
        self.active = False
        
        self.phase = 0.0
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.animate)
        # Don't start automatically — only when recording
        
    def start(self):
        self.active = True
        self.levels = [0.0] * self.history_size
        self.anim_timer.start(30)
        
    def stop(self):
        self.active = False
        self.anim_timer.stop()
        self.levels = [0.0] * self.history_size
        self.update()  # repaint as flat line
        
    def update_audio_level(self, level: float):
        if not self.active:
            return
            
        # Amplify significantly for better visuals
        level = min(1.0, level * 15.0)
            
        self.levels.pop(0)
        self.levels.append(level)

    def animate(self):
        self.phase -= 0.15 # shift phase left
        self.update() # trigger paintEvent
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        mid_y = h / 2.0
        
        # Transparent background so it fits into the UI seamlessly
        painter.fillRect(rect, QColor(0, 0, 0, 0))
        
        # 3 overlapping waves with different phases and colors (Premium Theme match)
        colors = [
            QColor(108, 60, 224, 180),  # #6c3ce0 (Theme Purple)
            QColor(236, 72, 153, 150),  # Pink
            QColor(139, 92, 246, 160)   # #8b5cf6 (Lighter Purple)
        ]
        
        for idx, color in enumerate(colors):
            path = QPainterPath()
            
            freq = 1.0 + (idx * 0.7)
            ph = self.phase * (1.0 + idx * 0.3)
            
            for i in range(self.history_size):
                x = (i / (self.history_size - 1)) * w
                
                # Smooth the level by averaging with neighbors for organic look
                if i > 0 and i < self.history_size - 1:
                    level = (self.levels[i-1] + self.levels[i] + self.levels[i+1]) / 3.0
                else:
                    level = self.levels[i]
                
                amp_max = h * 0.4
                # Baseline small wave even when silent
                amplitude = (level * amp_max) + (amp_max * 0.02)
                
                # Pinch ends to 0 using sine window
                window = math.sin((i / (self.history_size - 1)) * math.pi)
                
                y = mid_y + math.sin(ph + (i * 0.3 * freq)) * amplitude * window
                
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
                    
            pen = QPen(color, 2.0)
            painter.setPen(pen)
            
            # Gradient fill under the wave
            gradient = QLinearGradient(0, 0, 0, h)
            gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 10))
            gradient.setColorAt(0.5, QColor(color.red(), color.green(), color.blue(), 50))
            gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 10))
            
            painter.setBrush(gradient)
            
            # Close path to allow filling the shape nicely
            path.lineTo(w, mid_y)
            path.lineTo(0, mid_y)
            painter.drawPath(path)
