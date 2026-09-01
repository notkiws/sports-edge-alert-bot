from __future__ import annotations


def test_package_exposes_version() -> None:
    import sports_edge

    assert sports_edge.__version__
