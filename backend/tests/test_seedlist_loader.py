"""Seedlist parsing: .txt / .csv / .json, cloudflare_only filter, dedupe,
and the bundled-seedlist listing."""

from snihunter.sources.seedlist import list_bundled_seedlists, load_seedlist


def test_txt_comments_and_blanks(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text("# header\n\nexample.com\nfoo.example.com  # inline\n*.wild.com\n")
    hosts = [c.hostname for c in load_seedlist(p)]
    assert hosts == ["example.com", "foo.example.com", "wild.com"]


def test_txt_dedupe(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text("example.com\nEXAMPLE.COM\nexample.com\n")
    hosts = [c.hostname for c in load_seedlist(p)]
    assert hosts == ["example.com"]


def test_csv_with_header_and_cloudflare(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("domain,cloudflare\na.com,true\nb.com,false\nc.com,1\n")
    all_hosts = [c.hostname for c in load_seedlist(p)]
    assert all_hosts == ["a.com", "b.com", "c.com"]
    cf_only = [c.hostname for c in load_seedlist(p, cloudflare_only=True)]
    assert cf_only == ["a.com", "c.com"]


def test_json_array_of_strings(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('["a.com", "b.com", "*.c.com"]')
    hosts = [c.hostname for c in load_seedlist(p)]
    assert hosts == ["a.com", "b.com", "c.com"]


def test_json_objects_with_cloudflare(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('[{"domain":"a.com","cloudflare":true},{"domain":"b.com","cloudflare":false}]')
    cf_only = [c.hostname for c in load_seedlist(p, cloudflare_only=True)]
    assert cf_only == ["a.com"]


def test_unsupported_extension_raises(tmp_path):
    p = tmp_path / "s.xml"
    p.write_text("example.com")
    try:
        load_seedlist(p)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_bundled_seedlists_present():
    lists = list_bundled_seedlists()
    names = {x["name"] for x in lists}
    assert "safaricom-ke.txt" in names
    assert "airtel-ke.txt" in names
    assert "telkom-ke.txt" in names
    # Each bundled list must parse to at least one host.
    for x in lists:
        assert x["hosts"] > 0
