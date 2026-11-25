import errno

import server


def test_permission_error_is_human():
    message = server.friendly_error(PermissionError(13, "Отказано в доступе"))
    assert "Нет доступа" in message
    assert "WinError" not in message


def test_missing_folder_is_human():
    message = server.friendly_error(FileNotFoundError(2, "No such file"))
    assert "не найдена" in message
    assert "Errno" not in message


def test_busy_folder_is_human():
    error = OSError(errno.EBUSY, "resource busy")
    assert "занята" in server.friendly_error(error)


def test_unknown_error_hides_details():
    message = server.friendly_error(ValueError("internal boom xyz"))
    assert "boom" not in message
    assert "лог" in message
