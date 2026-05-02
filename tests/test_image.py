import pytest
from pathlib import Path
from extractors.image import ImageExtractor
from conftest import IMAGE_SAMPLE


def test_image_extractor_returns_result():
    ext = ImageExtractor()
    results = ext.extract(IMAGE_SAMPLE)
    assert isinstance(results, list)
    assert len(results) == 1


def test_image_extractor_source_type():
    ext = ImageExtractor()
    results = ext.extract(IMAGE_SAMPLE)
    assert results[0].source_type == "image"


def test_image_extractor_no_exception_on_all_jpegs():
    img_dir = Path("data/data factures et diverses")
    ext = ImageExtractor()
    for img_file in list(img_dir.glob("*.jpeg"))[:2]:  # test first 2 only (slow)
        results = ext.extract(img_file)
        assert isinstance(results, list)
