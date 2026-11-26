import history


def result(root="C:/upload-1"):
    return {
        "meta": {"root": root, "files_scanned": 1},
        "summary": {"score": 8.0, "error": 0, "warn": 0, "info": 0},
        "findings": [],
    }


def test_fingerprint_ignores_size_and_sees_names(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    for base in (left, right):
        (base / "ПЗ.docx").parent.mkdir(parents=True, exist_ok=True)
        (base / "ПЗ.docx").write_bytes(b"12345")
        (base / "АР.pdf").write_bytes(b"1234567")
    assert history.fingerprint(left) == history.fingerprint(right)

    (right / "ПЗ.docx").write_bytes(b"123456")
    assert history.fingerprint(left) == history.fingerprint(right)  # размер не важен

    (right / "ИОС.pdf").write_bytes(b"1")
    assert history.fingerprint(left) != history.fingerprint(right)  # состав важен


def test_explicit_key_links_different_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    key = "abcd1234"
    path = history.save(result(), key=key)
    assert path.name.endswith(f"-{key}.json")

    old = history.previous("C:/upload-2", exclude_last=False, key=key)
    assert old["meta"]["root"] == "C:/upload-1"
    assert history.list_runs("C:/upload-2", key=key)[0]["score"] == 8.0


def test_two_saves_in_one_second_do_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    first = history.save(result(), key="same0000")
    second = history.save(result(), key="same0000")
    assert first != second
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_folder_name_does_not_split_history(tmp_path):
    one = tmp_path / "проект-А"
    two = tmp_path / "проект-Б"
    for base in (one, two):
        base.mkdir()
        (base / "01-ПЗ.docx").write_bytes(b"x")
    assert history.fingerprint(one) == history.fingerprint(two)


def test_list_runs_reports_upload_source(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    payload = result()
    payload["meta"]["source"] = "upload"
    history.save(payload, key="upload00")
    runs = history.list_runs("C:/upload-1", key="upload00")
    assert runs[0]["source"] == "upload"


def test_saved_run_keeps_norms_passport(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    payload = result()
    payload["norms"] = [{
        "code": "СП 5.03.01-2020",
        "status": "действует",
        "replacement": "",
        "changed": "изм. № 1 (пост. № 33)",
        "source": "01-Справочник.md",
        "has_full_text": True,
    }]
    history.save(payload, key="norms000")

    saved = history.previous("C:/upload-1", exclude_last=False, key="norms000")
    assert saved["norms"] == payload["norms"]
