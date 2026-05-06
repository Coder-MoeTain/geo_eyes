from app.security import create_access_token


def test_access_token_generation():
    token = create_access_token("admin")
    assert isinstance(token, str)
    assert len(token) > 20
