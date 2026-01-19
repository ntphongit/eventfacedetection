"""Unit tests for person search functionality."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.services.face_service import (
    FaceService, SearchMatch, PersonSearchResult, OutputSummary
)
from src.exceptions import NoFaceDetectedError


@pytest.fixture
def mock_config():
    """Mock config that allows tmp_path directories."""
    def _mock(tmp_path):
        return {
            "storage": {"allowed_directories": [str(tmp_path)]},
            "files": {"allowed_formats": ["jpeg", "jpg", "png", "heic"]}
        }
    return _mock


class TestSearchPersonFolder:
    """Tests for search_person_folder method."""

    def test_extracts_person_name_from_folder(self, tmp_path, mock_config):
        """Person name extracted from folder path with underscores replaced."""
        folder = tmp_path / "Nguyen_Thanh_Phong"
        folder.mkdir()
        (folder / "test.jpg").write_bytes(b"fake")

        service = FaceService()
        with patch('src.services.face_service.get_config', return_value=mock_config(tmp_path)):
            with patch.object(service, 'search', return_value=[]):
                result = service.search_person_folder(str(folder))

        assert result.person_name == "Nguyen Thanh Phong"

    def test_returns_empty_when_no_images(self, tmp_path, mock_config):
        """Returns empty result for folder without images."""
        folder = tmp_path / "Empty_Person"
        folder.mkdir()

        service = FaceService()
        with patch('src.services.face_service.get_config', return_value=mock_config(tmp_path)):
            result = service.search_person_folder(str(folder))

        assert result.matches == []
        assert "No images found" in result.search_errors[0]

    def test_deduplicates_by_image_path_keeps_best(self, tmp_path, mock_config):
        """Keeps highest confidence per unique image_path."""
        folder = tmp_path / "Test_Person"
        folder.mkdir()
        (folder / "ref1.jpg").write_bytes(b"fake1")
        (folder / "ref2.jpg").write_bytes(b"fake2")

        match_low = SearchMatch("event/photo1.jpg", 0.3, 0.7)
        match_high = SearchMatch("event/photo1.jpg", 0.2, 0.8)
        match_other = SearchMatch("event/photo2.jpg", 0.25, 0.75)

        service = FaceService()
        call_count = [0]

        def mock_search(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return [match_low, match_other]
            return [match_high]

        with patch('src.services.face_service.get_config', return_value=mock_config(tmp_path)):
            with patch.object(service, 'search', side_effect=mock_search):
                result = service.search_person_folder(str(folder))

        assert len(result.matches) == 2
        photo1_match = next(m for m in result.matches if "photo1" in m.image_path)
        assert photo1_match.confidence == 0.8

    def test_handles_no_face_error_continues(self, tmp_path, mock_config):
        """Continues processing when image has no face."""
        folder = tmp_path / "Test_Person"
        folder.mkdir()
        (folder / "good.jpg").write_bytes(b"good")
        (folder / "bad.jpg").write_bytes(b"bad")

        service = FaceService()
        call_count = [0]

        def mock_search(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise NoFaceDetectedError()
            return [SearchMatch("event/photo.jpg", 0.2, 0.8)]

        with patch('src.services.face_service.get_config', return_value=mock_config(tmp_path)):
            with patch.object(service, 'search', side_effect=mock_search):
                result = service.search_person_folder(str(folder))

        assert len(result.matches) == 1
        assert any("No face" in err for err in result.search_errors)

    def test_reference_count_matches_image_count(self, tmp_path, mock_config):
        """Reference count reflects number of images in folder."""
        folder = tmp_path / "Test_Person"
        folder.mkdir()
        (folder / "ref1.jpg").write_bytes(b"1")
        (folder / "ref2.png").write_bytes(b"2")
        (folder / "ref3.jpeg").write_bytes(b"3")

        service = FaceService()
        with patch('src.services.face_service.get_config', return_value=mock_config(tmp_path)):
            with patch.object(service, 'search', return_value=[]):
                result = service.search_person_folder(str(folder))

        assert result.reference_count == 3

    def test_rejects_path_outside_allowed_directories(self, tmp_path):
        """Raises ValueError for folder outside allowed directories."""
        folder = tmp_path / "Test_Person"
        folder.mkdir()
        (folder / "test.jpg").write_bytes(b"fake")

        service = FaceService()
        with patch('src.services.face_service.get_config') as mock_cfg:
            mock_cfg.return_value = {
                "storage": {"allowed_directories": ["/some/other/path"]},
                "files": {"allowed_formats": ["jpg"]}
            }
            with pytest.raises(ValueError, match="not under allowed directories"):
                service.search_person_folder(str(folder))


class TestCopyMatchesToOutput:
    """Tests for copy_matches_to_output method."""

    def test_creates_person_folder(self, tmp_path):
        """Creates folder named after person with folder-prefixed filename."""
        output_root = tmp_path / "output"
        source_dir = tmp_path / "event_photos" / "MAY_01"
        source_dir.mkdir(parents=True)
        source_file = source_dir / "photo.jpg"
        source_file.write_bytes(b"image_data")

        # Use relative path like in real DB (folder/filename)
        result = PersonSearchResult(
            person_name="John Doe",
            matches=[SearchMatch("MAY_01/photo.jpg", 0.2, 0.8)],
            reference_count=1,
            search_errors=[]
        )

        service = FaceService()
        with patch('src.services.face_service.get_config') as mock_cfg:
            mock_cfg.return_value = {
                "person_search": {"output_root": str(output_root)}
            }
            service.resolve_image_path = lambda p: str(tmp_path / "event_photos" / p)
            output = service.copy_matches_to_output(result)

        assert (output_root / "John Doe").exists()
        # Filename prefixed with parent folder: MAY_01_photo.jpg
        assert (output_root / "John Doe" / "MAY_01_photo.jpg").exists()
        assert output.copied_count == 1

    def test_handles_duplicate_filenames_from_different_folders(self, tmp_path):
        """Handles same filename from different source folders."""
        output_root = tmp_path / "output"
        person_folder = output_root / "Test Person"
        person_folder.mkdir(parents=True)

        # Create two source files with same name in different folders
        for folder in ["MAY_01", "MAY_02"]:
            source_dir = tmp_path / "event_photos" / folder
            source_dir.mkdir(parents=True)
            (source_dir / "DSC07452.jpg").write_bytes(f"image_{folder}".encode())

        result = PersonSearchResult(
            person_name="Test Person",
            matches=[
                SearchMatch("MAY_01/DSC07452.jpg", 0.2, 0.8),
                SearchMatch("MAY_02/DSC07452.jpg", 0.25, 0.75),
            ],
            reference_count=1,
            search_errors=[]
        )

        service = FaceService()
        with patch('src.services.face_service.get_config') as mock_cfg:
            mock_cfg.return_value = {
                "person_search": {"output_root": str(output_root)}
            }
            service.resolve_image_path = lambda p: str(tmp_path / "event_photos" / p)
            output = service.copy_matches_to_output(result)

        # Each file prefixed with its source folder
        assert (person_folder / "MAY_01_DSC07452.jpg").exists()
        assert (person_folder / "MAY_02_DSC07452.jpg").exists()
        assert output.copied_count == 2

    def test_skips_missing_source_files(self, tmp_path):
        """Records missing files in skipped list."""
        output_root = tmp_path / "output"

        result = PersonSearchResult(
            person_name="Test Person",
            matches=[SearchMatch("/nonexistent/photo.jpg", 0.2, 0.8)],
            reference_count=1,
            search_errors=[]
        )

        service = FaceService()
        with patch('src.services.face_service.get_config') as mock_cfg:
            mock_cfg.return_value = {
                "person_search": {"output_root": str(output_root)}
            }
            service.resolve_image_path = lambda p: p
            output = service.copy_matches_to_output(result)

        assert output.copied_count == 0
        assert len(output.skipped_files) == 1
        assert "Missing" in output.skipped_files[0]

    def test_empty_matches_returns_zero_copied(self, tmp_path):
        """Returns 0 copied for empty matches list."""
        output_root = tmp_path / "output"

        result = PersonSearchResult(
            person_name="Test Person",
            matches=[],
            reference_count=1,
            search_errors=[]
        )

        service = FaceService()
        with patch('src.services.face_service.get_config') as mock_cfg:
            mock_cfg.return_value = {
                "person_search": {"output_root": str(output_root)}
            }
            output = service.copy_matches_to_output(result)

        assert output.copied_count == 0
        assert (output_root / "Test Person").exists()


class TestGetImagesFromFolder:
    """Tests for _get_images_from_folder helper."""

    def test_filters_by_extension(self, tmp_path, mock_config):
        """Only returns files with valid image extensions."""
        folder = tmp_path / "images"
        folder.mkdir()
        (folder / "photo1.jpg").write_bytes(b"1")
        (folder / "photo2.png").write_bytes(b"2")
        (folder / "document.txt").write_bytes(b"3")
        (folder / "video.mp4").write_bytes(b"4")

        service = FaceService()
        with patch('src.services.face_service.get_config', return_value=mock_config(tmp_path)):
            images = service._get_images_from_folder(str(folder))

        assert len(images) == 2
        names = {img.name for img in images}
        assert names == {"photo1.jpg", "photo2.png"}

    def test_ignores_subdirectories(self, tmp_path, mock_config):
        """Does not recurse into subdirectories."""
        folder = tmp_path / "images"
        folder.mkdir()
        (folder / "photo1.jpg").write_bytes(b"1")
        subfolder = folder / "subfolder"
        subfolder.mkdir()
        (subfolder / "photo2.jpg").write_bytes(b"2")

        service = FaceService()
        with patch('src.services.face_service.get_config', return_value=mock_config(tmp_path)):
            images = service._get_images_from_folder(str(folder))

        assert len(images) == 1
        assert images[0].name == "photo1.jpg"

    def test_limits_reference_count(self, tmp_path, mock_config):
        """Returns only max_refs images."""
        folder = tmp_path / "images"
        folder.mkdir()
        for i in range(10):
            (folder / f"photo{i}.jpg").write_bytes(b"x")

        service = FaceService()
        with patch('src.services.face_service.get_config', return_value=mock_config(tmp_path)):
            images = service._get_images_from_folder(str(folder), max_refs=5)

        assert len(images) == 5
