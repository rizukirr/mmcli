from unittest.mock import patch, AsyncMock, MagicMock
from app import cli


def test_main_invokes_download():
    mock_args = MagicMock()
    with (
        patch("app.cli.command_manager", return_value=mock_args) as mock_cm,
        patch(
            "app.cli.download", new=AsyncMock(return_value={"success": True})
        ) as mock_dl,
    ):
        cli.main()
        mock_cm.assert_called_once()
        mock_dl.assert_awaited_once_with(mock_args)


def test_main_handles_keyboard_interrupt(capsys):
    with patch("app.cli.command_manager", side_effect=KeyboardInterrupt):
        cli.main()
    out = capsys.readouterr().out
    assert "cancelled" in out.lower()
