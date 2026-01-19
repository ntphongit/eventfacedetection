"""Integration tests for search command folder mode."""
import pytest
from click.testing import CliRunner
from unittest.mock import patch

from src.cli.commands import cli
from src.services.face_service import SearchMatch, PersonSearchResult, OutputSummary


class TestSearchFolderMode:
    """Tests for search command with folder input."""

    def test_search_help_shows_options(self):
        """--help displays command options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])

        assert result.exit_code == 0
        assert "--limit" in result.output
        assert "--open" in result.output
        assert "folder" in result.output.lower()

    def test_folder_triggers_person_search(self, tmp_path):
        """Folder input triggers search_person_folder."""
        folder = tmp_path / "Test_Person"
        folder.mkdir()
        (folder / "ref.jpg").write_bytes(b"fake")

        mock_result = PersonSearchResult(
            person_name="Test Person",
            matches=[SearchMatch("event/photo.jpg", 0.2, 0.8)],
            reference_count=1,
            search_errors=[]
        )
        mock_output = OutputSummary(
            copied_count=1,
            output_path=str(tmp_path / "output" / "Test Person"),
            skipped_files=[]
        )

        runner = CliRunner()
        with patch('src.cli.commands.FaceService') as MockService:
            instance = MockService.return_value
            instance.search_person_folder.return_value = mock_result
            instance.copy_matches_to_output.return_value = mock_output

            result = runner.invoke(cli, ["search", str(folder)])

        assert result.exit_code == 0
        assert "Test Person" in result.output
        assert "Copied 1" in result.output
        instance.search_person_folder.assert_called_once()

    def test_displays_warnings(self, tmp_path):
        """Shows warnings from search errors."""
        folder = tmp_path / "Test_Person"
        folder.mkdir()
        (folder / "ref.jpg").write_bytes(b"fake")

        mock_result = PersonSearchResult(
            person_name="Test Person",
            matches=[],
            reference_count=1,
            search_errors=["No face: bad.jpg", "Timeout: slow.jpg"]
        )

        runner = CliRunner()
        with patch('src.cli.commands.FaceService') as MockService:
            instance = MockService.return_value
            instance.search_person_folder.return_value = mock_result

            result = runner.invoke(cli, ["search", str(folder)])

        assert result.exit_code == 0
        assert "Warnings" in result.output
        assert "No face: bad.jpg" in result.output

    def test_handles_no_matches(self, tmp_path):
        """Handles case with no matches found."""
        folder = tmp_path / "Test_Person"
        folder.mkdir()
        (folder / "ref.jpg").write_bytes(b"fake")

        mock_result = PersonSearchResult(
            person_name="Test Person",
            matches=[],
            reference_count=1,
            search_errors=[]
        )

        runner = CliRunner()
        with patch('src.cli.commands.FaceService') as MockService:
            instance = MockService.return_value
            instance.search_person_folder.return_value = mock_result

            result = runner.invoke(cli, ["search", str(folder)])

        assert result.exit_code == 0
        assert "No matches found" in result.output

    def test_limit_option_passed(self, tmp_path):
        """--limit option passed to search_person_folder."""
        folder = tmp_path / "Test_Person"
        folder.mkdir()
        (folder / "ref.jpg").write_bytes(b"fake")

        mock_result = PersonSearchResult(
            person_name="Test Person",
            matches=[],
            reference_count=1,
            search_errors=[]
        )

        runner = CliRunner()
        with patch('src.cli.commands.FaceService') as MockService:
            instance = MockService.return_value
            instance.search_person_folder.return_value = mock_result

            runner.invoke(cli, ["search", str(folder), "--limit", "50"])

        instance.search_person_folder.assert_called_once()
        call_args = instance.search_person_folder.call_args
        assert call_args[1]['limit'] == 50


class TestSearchFileMode:
    """Tests for search command with file input (backward compatibility)."""

    def test_file_triggers_single_search(self, tmp_path):
        """File input triggers single image search."""
        img_file = tmp_path / "query.jpg"
        img_file.write_bytes(b"fake image")

        runner = CliRunner()
        with patch('src.cli.commands.FaceService') as MockService:
            instance = MockService.return_value
            instance.search.return_value = []

            result = runner.invoke(cli, ["search", str(img_file)])

        assert result.exit_code == 0
        instance.search.assert_called_once()
        # search_person_folder should NOT be called
        instance.search_person_folder.assert_not_called()

    def test_file_with_matches_displays_results(self, tmp_path):
        """File search displays match results."""
        img_file = tmp_path / "query.jpg"
        img_file.write_bytes(b"fake image")

        match = SearchMatch("event/photo.jpg", 0.2, 0.8)

        runner = CliRunner()
        with patch('src.cli.commands.FaceService') as MockService:
            instance = MockService.return_value
            instance.search.return_value = [match]
            instance.resolve_image_path.return_value = "/full/path/photo.jpg"

            result = runner.invoke(cli, ["search", str(img_file)])

        assert result.exit_code == 0
        assert "Found 1 matches" in result.output
        assert "80.00%" in result.output  # confidence
