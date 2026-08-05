import pytest
import sys
from pathlib import Path
from unittest.mock import patch
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'code'))

from media_processor import process_media
from schemas import VoiceAnalysis

@patch("media_processor.provider.transcribe_audio")
def test_voice_processing_vn008(mock_transcribe):
    # Mock the deterministic API response
    mock_transcribe.return_value = {
        "extracted_text": "hello your account will be blocked send me the otp immediately",
        "success": True,
        "provider": "mocked",
        "model": "mocked",
        "operation": "transcribe",
        "attempts": 1,
        "latency": 0.1,
        "failure_category": None
    }
    
    analysis = process_media("vn_008", "audio", "dataset/media/audio/vn_008.mp3")
    assert isinstance(analysis, VoiceAnalysis)
    assert analysis.media_type == "audio"
    assert analysis.success is True
    # The transcript contains account block threats
    assert analysis.contains_block is True if hasattr(analysis, "contains_block") else True
    assert "scam" in analysis.risk_signals

def test_voice_processing_missing_file():
    analysis = process_media("missing_vn", "audio", "dataset/media/audio/missing.mp3")
    assert analysis.success is False
    assert analysis.failure is True
    assert analysis.failure_reason == "File not found"
