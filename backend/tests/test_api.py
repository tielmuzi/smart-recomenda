import time
from urllib.parse import parse_qs, urlparse

import jwt
from fastapi.testclient import TestClient
from backend.app import main

main.AUTH_CLIENT_ID = "test-auth-client"
main.AUTH_PORTAL_URL = "https://auth.example.test"
main.AUTH_API_URL = "https://api.example.test"
main.AUTH_JWT_SECRET = "test-only-session-secret"
main.AUTH_CALLBACK_URL = "http://localhost:3000/api/v1/auth/callback"
main.AUTH_COOKIE_SECURE = False
main.AUTH_COOKIE_SAMESITE = "lax"
main.ADMIN_IDS = {"test-user"}

session_token = jwt.encode(
    {
        "sub": "test-user",
        "appId": main.AUTH_CLIENT_ID,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    },
    main.AUTH_JWT_SECRET,
    algorithm="HS256",
)

client = TestClient(
    main.app,
    follow_redirects=False,
    cookies={main.AUTH_COOKIE_NAME: session_token},
    headers={"Origin": "http://localhost:3000"},
)


def test_health_and_catalog():
    assert client.get('/health').status_code == 200
    response = client.get('/api/v1/contents?limit=4')
    assert response.status_code == 200
    assert response.json()['total'] >= 4


def test_academic_demo_access_without_login():
    anonymous = TestClient(main.app)
    assert anonymous.get('/api/v1/auth/config').json()['demo_access'] is True
    profile = anonymous.get('/api/v1/auth/me')
    assert profile.status_code == 200
    assert profile.json()['user_id'] == main.DEMO_USER
    assert profile.json()['demo'] is True
    assert anonymous.get('/api/v1/preferences').status_code == 200
    assert anonymous.get('/api/v1/profile', headers={'x-smart-user': 'admin-spoof'}).json()['user_id'] == main.DEMO_USER
    assert anonymous.get('/api/v1/admin/metrics').status_code == 403
    assert main.is_admin(main.DEMO_USER) is False


def test_invalid_stale_session_falls_back_to_academic_visitor():
    stale_client = TestClient(
        main.app,
        cookies={main.AUTH_COOKIE_NAME: 'expired-or-corrupted-session'},
    )
    response = stale_client.get('/api/v1/auth/me')
    assert response.status_code == 200
    assert response.json()['user_id'] == main.DEMO_USER
    assert response.json()['demo'] is True
    assert any(
        cookie.startswith(f'{main.AUTH_COOKIE_NAME}=')
        and ('Max-Age=0' in cookie or 'expires=' in cookie.lower())
        for cookie in response.headers.get_list('set-cookie')
    )
    assert stale_client.get('/api/v1/recommendations').status_code == 200


def test_personal_routes_require_a_valid_session_when_demo_access_is_disabled(monkeypatch):
    monkeypatch.setattr(main, 'DEMO_ACCESS', False)
    anonymous = TestClient(main.app)
    assert anonymous.get('/api/v1/preferences').status_code == 401
    assert anonymous.get('/api/v1/preferences', headers={'x-smart-user': 'test-user'}).status_code == 401
    assert client.post('/api/v1/favorites/101', headers={'Origin': 'https://attacker.example'}).status_code == 403

    wrong_app_token = jwt.encode(
        {"sub": "test-user", "appId": "another-app", "exp": int(time.time()) + 3600},
        main.AUTH_JWT_SECRET,
        algorithm="HS256",
    )
    invalid = TestClient(main.app, cookies={main.AUTH_COOKIE_NAME: wrong_app_token})
    assert invalid.get('/api/v1/preferences').status_code == 401


def test_valid_platform_session_can_be_provisioned():
    preview_token = jwt.encode(
        {
            "sub": "preview-user-01",
            "appId": main.AUTH_CLIENT_ID,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        main.AUTH_JWT_SECRET,
        algorithm="HS256",
    )
    preview_client = TestClient(main.app, cookies={main.AUTH_COOKIE_NAME: preview_token})
    response = preview_client.get('/api/v1/auth/me')
    assert response.status_code == 200
    assert response.json()['user_id'] == 'preview-user-01'


def test_manus_oauth_login_binds_state_to_browser(monkeypatch):
    oauth_client = TestClient(main.app, follow_redirects=False, headers={"Origin": "http://localhost:3000"})
    response = oauth_client.get('/api/v1/auth/login')
    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers['location']).query)
    assert query['appId'] == [main.AUTH_CLIENT_ID]
    assert query['responseType'] == ['code']
    state_payload = main.decode_state(query['state'][0])
    assert state_payload['redirectUri'] == main.AUTH_CALLBACK_URL
    assert oauth_client.cookies.get('smartrecomenda_oauth_nonce') == state_payload['nonce']
    mismatch_state = main.encoded_state({'redirectUri': main.AUTH_CALLBACK_URL, 'nonce': 'wrong'})
    mismatch_client = TestClient(
        main.app,
        cookies={'smartrecomenda_oauth_nonce': state_payload['nonce']},
    )
    mismatch = mismatch_client.get('/api/v1/auth/callback', params={'code': 'test-code', 'state': mismatch_state})
    assert mismatch.status_code == 400

    monkeypatch.setattr(main, 'exchange_auth_code', lambda code, redirect_uri: {
        'openId': 'oauth-user-01',
        'name': 'Usuária Manus',
        'email': 'user@example.test',
    })
    callback = oauth_client.get('/api/v1/auth/callback', params={'code': 'test-code', 'state': query['state'][0]})
    assert callback.status_code == 303
    assert callback.headers['location'] == '/'
    assert callback.cookies.get(main.AUTH_COOKIE_NAME)
    assert oauth_client.get('/api/v1/auth/me').json()['user_id'] == 'oauth-user-01'
    assert oauth_client.post('/api/v1/auth/logout', headers={'Origin': 'http://localhost:3000'}).json() == {'ok': True}
    assert oauth_client.get('/api/v1/auth/me').json()['user_id'] == main.DEMO_USER


def test_recommendations_are_explainable():
    response = client.get('/api/v1/recommendations')
    assert response.status_code == 200
    payload = response.json()
    assert payload['strategy'] == 'HybridStrategy'
    assert payload['items']
    assert all(item['reason'] for item in payload['items'])
    assert payload['formula'] == '0.44E + 0.34H + 0.10Q + 0.12P'


def test_saved_feedback_changes_recommendations_and_can_hide_items():
    user_id = 'recommendation-learning-test-user'
    with main.db() as connection:
        connection.execute("DELETE FROM interactions WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM favorites WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM ratings WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM recommendation_events WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM preferences WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM profiles WHERE user_id=?", (user_id,))
    main.provision_user(user_id, 'Recomendação Teste', None)
    with main.db() as connection:
        connection.execute(
            "UPDATE preferences SET genres='[]',types=?,languages=? WHERE user_id=?",
            ('["Filme","Série","Música","Notícia"]', '["Português","Inglês"]', user_id),
        )
    before = {item['id']: item['score'] for item in main.recommendations(user_id)[0]}
    token = jwt.encode(
        {
            "sub": user_id,
            "appId": main.AUTH_CLIENT_ID,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        main.AUTH_JWT_SECRET,
        algorithm='HS256',
    )
    personalized = TestClient(
        main.app,
        cookies={main.AUTH_COOKIE_NAME: token},
        headers={"Origin": "http://localhost:3000"},
    )
    assert personalized.post('/api/v1/interactions/105', json={'kind': 'view'}).status_code == 200
    after_view = {item['id']: item['score'] for item in main.recommendations(user_id)[0]}
    assert after_view[102] > before[102]

    assert personalized.post('/api/v1/favorites/105').status_code == 200
    after = {item['id']: item for item in main.recommendations(user_id)[0]}
    assert after[102]['score'] > after_view[102]
    assert 'suas avaliações e itens salvos' in after[102]['reason']

    assert personalized.post('/api/v1/favorites/105').status_code == 200
    assert personalized.post('/api/v1/ratings/105', json={'rating': 1}).status_code == 200
    after_negative_rating = {item['id']: item for item in main.recommendations(user_id)[0]}
    assert after_negative_rating[102]['score'] < before[102]

    hidden = personalized.post('/api/v1/interactions/102', json={'kind': 'hide'})
    assert hidden.status_code == 200
    assert 102 not in {item['id'] for item in main.recommendations(user_id)[0]}

    with main.db() as connection:
        connection.execute("DELETE FROM interactions WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM favorites WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM ratings WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM recommendation_events WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM preferences WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM profiles WHERE user_id=?", (user_id,))


def test_preferences_and_favorites_persist():
    prefs = {'types': ['Filme'], 'genres': ['Tecnologia'], 'languages': ['Português'], 'blocked_ids': [], 'diversity': 'foco'}
    assert client.put('/api/v1/preferences', json=prefs).status_code == 200
    assert client.get('/api/v1/preferences').json()['diversity'] == 'foco'
    toggle = client.post('/api/v1/favorites/101')
    assert toggle.status_code == 200
    assert client.get('/api/v1/favorites').status_code == 200


def test_admin_metrics_have_demo_label():
    response = client.get('/api/v1/admin/metrics')
    assert response.status_code == 200
    metrics = response.json()
    assert 'demonstrativos' in metrics['data_label'].lower()
    assert metrics['active_users'] >= 0
    assert metrics['recommendations'] >= 0
    assert len(metrics['daily_activity']) == 7
    assert isinstance(metrics['top_contents'], list)
    assert isinstance(metrics['recent_activity'], list)
