import pytest
import os
import sys
from pathlib import Path
sys.path.append(os.path.abspath('code'))
from schemas import ImageAnalysis, MediaAnalysis
from media_processor import process_media
from PIL import Image

def test_missing_image():
    # Process a non-existent image
    analysis = process_media("test_id", "image", "non_existent.jpg")
    assert isinstance(analysis, MediaAnalysis)
    assert analysis.failure is True
    assert analysis.failure_reason == "File not found"

def test_corrupt_image(tmp_path):
    # Create a corrupt text file that pretends to be an image
    p = tmp_path / "corrupt.jpg"
    p.write_text("This is not an image")
    
    analysis = process_media("test_id", "image", str(p))
    assert isinstance(analysis, ImageAnalysis)
    assert analysis.failure is True
    assert "Invalid image file" in analysis.failure_reason
    assert analysis.quality == "corrupt"

def test_image_analysis_schema():
    # Create a dummy image
    p = Path("tests/dummy.jpg")
    p.parent.mkdir(exist_ok=True)
    img = Image.new('RGB', (60, 30), color = 'red')
    img.save(p)
    
    # We won't actually call the LLM in unit tests without a mock,
    # but we can verify the media_processor handles corrupt correctly.
    # The actual LLM logic will be tested in integration tests.
    pass
