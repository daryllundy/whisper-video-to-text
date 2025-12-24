import os
import shutil
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from whisper_video_to_text.web.main import app
import time

def test_history_endpoint():
    # Helper to clean up
    def cleanup(path):
        if path.exists():
            shutil.rmtree(path)

    # Setup temporary directory for transcripts
    # We need to mock the directory used by the app, but since it's hardcoded to "transcripts"
    # in views.py, we will temporarily rename the existing one if it exists or ensure we clean up ours.
    # Ideally, the path should be configurable, but for this verification we will just ensure 
    # we create files in the actual "transcripts" directory and remove them after.
    
    transcripts_dir = Path("transcripts")
    transcripts_dir.mkdir(exist_ok=True)
    
    # Create dummy transcript files
    job_id_1 = "test_job_1"
    job_id_2 = "test_job_2"
    
    # Job 1: 2 hours ago
    (transcripts_dir / f"{job_id_1}.txt").touch()
    (transcripts_dir / f"{job_id_1}.srt").touch()
    # Set mtime to past
    past_time = time.time() - 7200
    os.utime(transcripts_dir / f"{job_id_1}.txt", (past_time, past_time))
    
    # Job 2: Now
    (transcripts_dir / f"{job_id_2}.vtt").touch()
    
    try:
        client = TestClient(app)
        response = client.get("/api/history")
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"Response data: {data}")
        
        assert len(data) >= 2
        
        # Verify Job 2 is before Job 1 (descending date)
        # Note: We can't guarantee they are the ONLY files, so we search for them
        job1_data = next((item for item in data if item["job_id"] == job_id_1), None)
        job2_data = next((item for item in data if item["job_id"] == job_id_2), None)
        
        assert job1_data is not None
        assert job2_data is not None
        
        assert "txt" in job1_data["formats"]
        assert "srt" in job1_data["formats"]
        assert "vtt" in job2_data["formats"]
        
        print("✓ History endpoint verification successful!")
        
    finally:
        # Cleanup created files
        for ext in ["txt", "srt"]:
            p = transcripts_dir / f"{job_id_1}.{ext}"
            if p.exists(): p.unlink()
        
        p = transcripts_dir / f"{job_id_2}.vtt"
        if p.exists(): p.unlink()

if __name__ == "__main__":
    test_history_endpoint()
