from integrity_checker.db.models import User


def test_create_user():
    from integrity_checker.db.session import get_session
    session = get_session()
    # Clean up any existing test user first
    existing = session.query(User).filter_by(username="testuser").first()
    if existing:
        session.delete(existing)
        session.commit()
    user = User(username="testuser", password_hash="hashed", role="user")
    session.add(user)
    session.commit()
    assert user.id is not None
    assert user.username == "testuser"
    session.close()
