# for any tests that doesn't seem to fit anywhere else
from config import SOURCE_WEIGHTS, PLATFORM_IDS, PLATFORMS


def test_check_no_duplicate_platforms():
    """Checks that platform IDs are unique"""
    assert len(set(PLATFORM_IDS)) == len(PLATFORM_IDS)


def test_source_weight_id_check():
    """ 
    Checks that the source weight dictionary/hashmap contains all the sources in platforms
    """
    for platform in PLATFORMS:
        id = platform["id"]
        assert id in SOURCE_WEIGHTS, f"Missing Platform in source weights: {id}"


def test_source_weights_normal():
    """ Check that the source weight are normalized and sum up to 1
    """
    s = 0.0
    for key, val in SOURCE_WEIGHTS.items():
        s += val
    assert s == 1.0, "Source Weights DO NOT add up to 1.0, please modify the values."