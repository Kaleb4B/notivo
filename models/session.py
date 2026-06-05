import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

@dataclass
class SessionMetadata:
    title: str
    created_at: str
    duration: int
    language: str
    summary_generated: bool
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SessionMetadata':
        return cls(
            title=data.get('title', 'Meeting Session'),
            created_at=data.get('created_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            duration=data.get('duration', 0),
            language=data.get('language', 'auto'),
            summary_generated=data.get('summary_generated', False)
        )
        
    def to_dict(self) -> dict:
        return asdict(self)

class Session:
    def __init__(self, folder_path: Path):
        self.folder_path = folder_path
        self.metadata_file = folder_path / "metadata.json"
        self.audio_file = folder_path / "recording.wav"
        self.transcript_file = folder_path / "transcript.txt"
        self.summary_file = folder_path / "summary.md"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> SessionMetadata:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return SessionMetadata.from_dict(data)
            except Exception:
                pass
        
        # Default metadata if doesn't exist
        created_at = self.folder_path.name.replace("_", " ") if len(self.folder_path.name) == 19 else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return SessionMetadata(
            title="Meeting Session",
            created_at=created_at,
            duration=0,
            language="auto",
            summary_generated=False
        )

    def save_metadata(self):
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata.to_dict(), f, indent=4)
        except Exception:
            pass
