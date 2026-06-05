import os
import shutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List

from utils.config import config
from utils.logger import logger
from models.session import Session

class SessionManager:
    def __init__(self):
        self._ensure_root_dir()

    @property
    def root_dir(self) -> Path:
        path_str = config.get("storage_folder")
        if not path_str:
            from utils.constants import DEFAULT_SESSIONS_DIR
            path_str = str(DEFAULT_SESSIONS_DIR)
        return Path(path_str)

    def _ensure_root_dir(self):
        try:
            self.root_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create sessions directory: {e}")

    def create_new_session(self) -> Session:
        self._ensure_root_dir()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_folder = self.root_dir / timestamp
        session_folder.mkdir(parents=True, exist_ok=True)
        
        session = Session(session_folder)
        session.metadata.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session.save_metadata()
        logger.info(f"Created new session: {session_folder}")
        return session

    def get_all_sessions(self) -> List[Session]:
        sessions = []
        if not self.root_dir.exists():
            return sessions
            
        for folder in self.root_dir.iterdir():
            if folder.is_dir() and (folder / "metadata.json").exists():
                sessions.append(Session(folder))
                
        # Sort by creation time, descending
        sessions.sort(key=lambda s: s.metadata.created_at, reverse=True)
        return sessions

    def delete_session(self, session: Session) -> bool:
        try:
            if session.folder_path.exists():
                shutil.rmtree(session.folder_path)
            logger.info(f"Deleted session: {session.folder_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session.folder_path}: {e}")
            return False

    @staticmethod
    def open_in_explorer(path: Path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            logger.error(f"Failed to open explorer for {path}: {e}")

    @staticmethod
    def export_text(source_path: Path, target_path: Path):
        try:
            shutil.copy2(source_path, target_path)
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
