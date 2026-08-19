import os
import tempfile
import pytest

from app import create_app, db, User

@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///' + path, SECRET_KEY='test')
    db.session.remove()
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client
    with app.app_context(): db.session.remove()
    os.unlink(path)

def test_home(client):
    assert client.get('/').status_code == 200

def test_register_login(client):
    r=client.post('/register',data={'name':'Test Rider','email':'rider@example.com','phone':'08000000000','password':'secret1','role':'rider'},follow_redirects=True)
    assert r.status_code==200
    r=client.get('/dashboard')
    assert r.status_code==200

def test_location_requires_auth(client):
    assert client.post('/location',data={'latitude':6.5,'longitude':3.3}).status_code==401
