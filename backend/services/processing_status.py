"""Track async processing status of ingested files"""
from typing import Dict, Any
import threading
from datetime import datetime

class ProcessingStatusTracker:
    """Thread-safe tracker for background processing tasks"""
    
    def __init__(self):
        self.statuses: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def start_processing(self, file_id: str, file_type: str, filename: str):
        """Mark a file as started processing"""
        with self.lock:
            self.statuses[file_id] = {
                "status": "processing",
                "file_type": file_type,
                "filename": filename,
                "started_at": datetime.now().isoformat(),
                "progress": 0,
                "error": None
            }
    
    def update_progress(self, file_id: str, progress: int, message: str = None):
        """Update processing progress"""
        with self.lock:
            if file_id in self.statuses:
                self.statuses[file_id]["progress"] = progress
                if message:
                    self.statuses[file_id]["message"] = message
    
    def complete_processing(self, file_id: str, result_data: Dict[str, Any] = None):
        """Mark a file as completed processing"""
        with self.lock:
            if file_id in self.statuses:
                self.statuses[file_id]["status"] = "completed"
                self.statuses[file_id]["progress"] = 100
                self.statuses[file_id]["completed_at"] = datetime.now().isoformat()
                if result_data:
                    self.statuses[file_id].update(result_data)
    
    def fail_processing(self, file_id: str, error: str):
        """Mark a file as failed processing"""
        with self.lock:
            if file_id in self.statuses:
                self.statuses[file_id]["status"] = "failed"
                self.statuses[file_id]["error"] = error
                self.statuses[file_id]["completed_at"] = datetime.now().isoformat()
    
    def get_status(self, file_id: str) -> Dict[str, Any]:
        """Get status of a processing file"""
        with self.lock:
            return self.statuses.get(file_id, {"status": "not_found"})
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get all processing statuses"""
        with self.lock:
            return dict(self.statuses)
    
    def cleanup_old_entries(self, max_age_hours: int = 24):
        """Remove old processing entries"""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self.lock:
            to_remove = []
            for file_id, status in self.statuses.items():
                if status["status"] in ["completed", "failed"]:
                    if "completed_at" in status:
                        try:
                            completed = datetime.fromisoformat(status["completed_at"])
                            if completed < cutoff_time:
                                to_remove.append(file_id)
                        except:
                            pass
            
            for file_id in to_remove:
                del self.statuses[file_id]

# Global tracker instance
processing_tracker = ProcessingStatusTracker()
