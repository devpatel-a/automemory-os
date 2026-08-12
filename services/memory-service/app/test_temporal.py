from app.understanding.temporal_parser import extract_temporal_information


def test_temporal_information_extraction():
    res1 = extract_temporal_information("I study Python every evening.")
    assert len(res1) > 0

    res2 = extract_temporal_information("I bought a Tesla yesterday.")
    assert len(res2) > 0