"""
Tests for event endpoints
"""
import pytest
from fastapi import status

TEST_EVENT = {
    "session_id": "test-session-1",
    "event_type": "page_view",
    "properties": {
        "page": "home",
        "referrer": "google"
    }
}

@pytest.mark.asyncio
async def test_ingest_single_event(client, auth_headers):
    """Test ingesting single event"""
    response = await client.post(
        "/api/v1/events/",
        json=TEST_EVENT,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["session_id"] == TEST_EVENT["session_id"]
    assert data["event_type"] == TEST_EVENT["event_type"]
    assert "event_id" in data

@pytest.mark.asyncio
async def test_ingest_event_batch(client, auth_headers):
    """Test ingesting event batch"""
    events = [TEST_EVENT, TEST_EVENT]
    response = await client.post(
        "/api/v1/events/batch",
        json={"events": events},
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    for event in data:
        assert "event_id" in event

@pytest.mark.asyncio
async def test_get_session_events(client, auth_headers):
    """Test getting session events"""
    # First create an event
    await client.post(
        "/api/v1/events/",
        json=TEST_EVENT,
        headers=auth_headers
    )
    
    # Then get session events
    response = await client.get(
        f"/api/v1/events/sessions/{TEST_EVENT['session_id']}/summary",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["session_id"] == TEST_EVENT["session_id"]
    assert data["event_count"] > 0

@pytest.mark.asyncio
async def test_get_recent_sessions(client, auth_headers):
    """Test getting recent sessions"""
    response = await client.get(
        "/api/v1/events/sessions/recent",
        params={"limit": 5},
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "sessions" in data
    assert isinstance(data["sessions"], list)