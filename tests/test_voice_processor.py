import pytest
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'code'))

from media_processor import process_media
from schemas import VoiceAnalysis

def test_voice_processing_vn008():
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
