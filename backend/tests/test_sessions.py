from tests.conftest import OBJECTIVE


def test_create_session_allocates_devices(client, open_session):
    assert open_session["status"] == "aberta"
    assert open_session["allocated_device_ids"] == ["dev-03", "dev-04"]
    assert open_session["action_log"][0]["action"] == "Sessão aberta"
    device = client.get("/api/v1/devices/dev-03").json()
    assert device["status"] == "em_uso"


def test_create_session_rejects_unavailable_device(client):
    response = client.post(
        "/api/v1/sessions",
        json={
            "classroom_id": "cls-7a",
            "teacher_name": "Prof. Teste",
            "objective": OBJECTIVE,
            "device_ids": ["dev-01"],
        },
    )

    assert response.status_code == 409


def test_create_session_rejects_unknown_references(client):
    base = {"teacher_name": "Prof. Teste", "objective": OBJECTIVE}

    unknown_classroom = client.post(
        "/api/v1/sessions", json={**base, "classroom_id": "cls-x"}
    )
    unknown_device = client.post(
        "/api/v1/sessions",
        json={**base, "classroom_id": "cls-7a", "device_ids": ["dev-99"]},
    )

    assert unknown_classroom.status_code == 404
    assert unknown_device.status_code == 404


def test_create_session_validates_payload(client):
    response = client.post(
        "/api/v1/sessions",
        json={"classroom_id": "cls-7a", "teacher_name": "Pr", "objective": "curto"},
    )

    assert response.status_code == 422


def test_close_session_releases_devices_and_cannot_close_twice(client, open_session):
    url = f"/api/v1/sessions/{open_session['id']}/close"

    closed = client.patch(url, json={"justification": "Aula concluída e aparelhos conferidos."})
    again = client.patch(url, json={"justification": "Aula concluída e aparelhos conferidos."})

    assert closed.status_code == 200
    assert closed.json()["status"] == "encerrada"
    assert closed.json()["ended_at"] is not None
    assert closed.json()["action_log"][-1]["action"] == "Sessão encerrada"
    assert client.get("/api/v1/devices/dev-03").json()["status"] == "disponivel"
    assert again.status_code == 409


def test_filter_sessions_by_status(client):
    response = client.get("/api/v1/sessions", params={"session_status": "encerrada"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["sess-02"]


def test_get_unknown_session_returns_404(client):
    assert client.get("/api/v1/sessions/sess-x").status_code == 404


CLASS_CODE_ALPHABET = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")


def test_demo_sessions_have_fixed_class_codes(client):
    assert client.get("/api/v1/sessions/sess-01").json()["class_code"] == "AULA8B"
    assert client.get("/api/v1/sessions/sess-02").json()["class_code"] == "AULA7A"


def test_new_session_gets_a_short_unique_class_code(client, open_session):
    other = client.post(
        "/api/v1/sessions",
        json={"classroom_id": "cls-7a", "teacher_name": "Prof. Teste", "objective": OBJECTIVE},
    ).json()

    codes = [open_session["class_code"], other["class_code"]]
    for code in codes:
        assert len(code) == 6
        assert set(code) <= CLASS_CODE_ALPHABET
    assert len(set(codes + ["AULA8B", "AULA7A"])) == 4
