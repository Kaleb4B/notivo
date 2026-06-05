import queue
import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtCore import QThread, Signal
from utils.constants import SAMPLE_RATE, CHANNELS, CHUNK_SIZE
from utils.logger import logger
from utils.config import config

class AudioWorker(QThread):
    error_occurred = Signal(str)
    audio_level = Signal(float)
    audio_data_visualizer = Signal(np.ndarray)  # For raw waveform drawing
    
    def __init__(self, audio_file_path, audio_queue: queue.Queue):
        super().__init__()
        self.audio_file_path = audio_file_path
        self.audio_queue = audio_queue
        self.is_running = False
        self.is_paused = False
        self._q = queue.Queue()
        self.stream = None
        self.duration = 0  # in seconds

    def _callback(self, indata, frames, time, status):
        if status:
            logger.warning(f"Audio status: {status}")
        if not self.is_paused:
            data = indata.copy()
            self._q.put(data)
            
    def run(self):
        self.is_running = True
        self.duration = 0
        try:
            device_idx = config.get("input_device", -1)
            
            # Auto-detect MacBook microphone if not explicitly set
            if device_idx == -1:
                try:
                    devices = sd.query_devices()
                    for idx, dev in enumerate(devices):
                        name = dev.get("name", "")
                        if dev.get("max_input_channels", 0) > 0 and ("MacBook" in name or "Built-in" in name):
                            device_idx = idx
                            break
                except Exception as e:
                    logger.warning(f"Auto-detect mic failed: {e}")
                    
            device = None if device_idx == -1 else device_idx
            
            with sf.SoundFile(self.audio_file_path, mode='w', samplerate=SAMPLE_RATE, channels=CHANNELS) as file:
                with sd.InputStream(device=device, samplerate=SAMPLE_RATE, channels=CHANNELS, callback=self._callback, blocksize=1024):
                    while self.is_running:
                        try:
                            data = self._q.get(timeout=0.05)
                            self._process_chunk(data, file)
                        except queue.Empty:
                            pass
                
                # Drain remaining chunks after InputStream stops
                logger.info(f"AudioWorker: Input stream stopped. Draining remaining {self._q.qsize()} chunks.")
                while not self._q.empty():
                    try:
                        data = self._q.get_nowait()
                        self._process_chunk(data, file)
                    except queue.Empty:
                        break
        except Exception as e:
            logger.error(f"AudioWorker error: {e}")
            self.error_occurred.emit(str(e))

    def _process_chunk(self, data, file):
        # Emit audio level from QThread (reliable cross-thread)
        level = float(np.max(np.abs(data)))
        self.audio_level.emit(level)
        self.audio_data_visualizer.emit(data)
        
        # Write to file
        file.write(data)
        # Put to transcription queue
        try:
            self.audio_queue.put_nowait(data)
        except queue.Full:
            pass
        
        self.duration += len(data) / SAMPLE_RATE
            
    def stop(self):
        self.is_running = False
        
    def pause(self):
        self.is_paused = True
        
    def resume(self):
        self.is_paused = False
