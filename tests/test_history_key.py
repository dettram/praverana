import history


def result(root="C:/upload-1"):
    return {
        "meta": {"root": root, "files_scanned": 1},
        "summary": {"score": 8.0, "error": 0, "warn": 0, "info": 0},
        "findings": [],
    }


def test_fingerprint_same_tree_and_different_size(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    for base in (left, right):
        (base / "ПЗ.docx").parent.mkdir(parents=True, exist_ok=True)
        (base / "ПЗ.docx").write_bytes(b"12345")
        (base / "АР.pdf").write_bytes(b"1234567")
    assert history.fingerprint(left) == history.fingerprint(right)

    (right / "ПЗ.docx").write_bytes(b"123456")
    assert history.fingerprint(left) != history.fingerprint(right)


def test_explicit_key_links_different_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    key = "abcd1234"
    path = history.save(result(), key=key)
    assert path.name.endswith(f"-{key}.json")

    old = history.previous("C:/upload-2", exclude_last=False, key=key)
    assert old["meta"]["root"] == "C:/upload-1"
    assert history.list_runs("C:/upload-2", key=key)[0]["score"] == 8.0


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
