from unittest.mock import patch, AsyncMock, MagicMock
import main


def test_main_invokes_download():
    mock_args = MagicMock()
    with patch("main.command_manager", return_value=mock_args) as mock_cm, \
         patch("main.download", new=AsyncMock(return_value={"success": True})) as mock_dl:
        main.main()
        mock_cm.assert_called_once()
        mock_dl.assert_awaited_once_with(mock_args)


def test_main_handles_keyboard_interrupt(capsys):
    with patch("main.command_manager", side_effect=KeyboardInterrupt):
        main.main()
    out = capsys.readouterr().out
    assert "cancelled" in out.lower()
