import history


def result(root="C:/upload-1", source="path"):
    return {
        "meta": {"root": root, "files_scanned": 1, "source": source},
        "summary": {"score": 8.0, "error": 0, "warn": 0, "info": 0},
        "findings": [],
    }


def test_fingerprint_tracks_composition_not_size(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    for base in (left, right):
        (base / "ПЗ.docx").parent.mkdir(parents=True, exist_ok=True)
        (base / "ПЗ.docx").write_bytes(b"12345")
        (base / "АР.pdf").write_bytes(b"1234567")
    assert history.fingerprint(left) == history.fingerprint(right)

    # Исправление документа меняет размер, но не состав — история не рвётся.
    (right / "ПЗ.docx").write_bytes(b"123456")
    assert history.fingerprint(left) == history.fingerprint(right)

    (right / "Новый.docx").write_bytes(b"1")
    assert history.fingerprint(left) != history.fingerprint(right)


def test_dataset_key_links_path_and_upload(tmp_path):
    path = tmp_path / "АТЛАС"
    upload = tmp_path / "incoming" / "АТЛАС"
    for base in (path, upload):
        base.mkdir(parents=True)
        (base / "ПЗ.docx").write_bytes(b"1")
        (base / "АР.pdf").write_bytes(b"2")

    assert history.dataset_key(path) == history.dataset_key(
        upload, source_name="АТЛАС")


def test_explicit_key_links_different_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    key = "abcd1234"
    path = history.save(result(), key=key)
    assert path.name.endswith(f"-{key}.json")

    old = history.previous("C:/upload-2", exclude_last=False, key=key)
    assert old["meta"]["root"] == "C:/upload-1"
    assert history.list_runs("C:/upload-2", key=key)[0]["score"] == 8.0


def test_save_twice_does_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    first = history.save(result())
    second = history.save(result())
    assert first != second
    assert first.exists() and second.exists()


def test_list_runs_marks_browser_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    history.save(result(source="upload"), key="browser1")
    run = history.list_runs("C:/upload-1", key="browser1")[0]
    assert run["source"] == "upload"
