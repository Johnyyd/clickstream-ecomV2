"""
Tests for auth endpoints
"""
import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_login_success(client, test_user):
    """Test successful login"""
    response = await client.post(
        "/api/v1/auth/token",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    """Test login with wrong password"""
    response = await client.post(
        "/api/v1/auth/token",
        data={
            "username": "testuser",
            "password": "wrongpass"
        }
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_protected_endpoint(client, auth_headers):
    """Test accessing protected endpoint"""
    response = await client.get(
        "/api/v1/products/",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK

@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client):
    """Test accessing protected endpoint without token"""
    response = await client.get("/api/v1/products/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED