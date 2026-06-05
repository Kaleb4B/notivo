import sounddevice as sd
from utils.logger import logger

def get_default_microphone():
    try:
        return sd.default.device[0]
    except Exception as e:
        logger.error(f"Failed to get default microphone: {e}")
        return None

def check_microphone_available() -> bool:
    try:
        devices = sd.query_devices()
        for d in devices:
            if d.get('max_input_channels', 0) > 0:
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking microphone: {e}")
        return False
