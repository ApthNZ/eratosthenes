"""
Tests for feed management functionality.
"""
import pytest
from httpx import AsyncClient
import base64


@pytest.fixture
def auth_headers():
    """Basic auth headers for eratosthenes:eratosthenes."""
    credentials = base64.b64encode(b"eratosthenes:eratosthenes").decode()
    return {"Authorization": f"Basic {credentials}"}


@pytest.mark.asyncio
async def test_feeds_manage_page_requires_auth(client: AsyncClient):
    """Test that feed management page requires authentication."""
    response = await client.get("/feeds-manage")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_feeds_manage_page_with_auth(client: AsyncClient, auth_headers):
    """Test that feed management page is accessible with auth."""
    response = await client.get("/feeds-manage", headers=auth_headers)
    assert response.status_code == 200
    assert b"Manage RSS Feeds" in response.content


@pytest.mark.asyncio
async def test_delete_feed_requires_auth(client: AsyncClient):
    """Test that DELETE /api/feeds/:id requires authentication."""
    response = await client.delete("/api/feeds/999")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_feed_not_found(client: AsyncClient, auth_headers):
    """Test deleting a non-existent feed returns 404."""
    response = await client.delete("/api/feeds/999999", headers=auth_headers)
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_delete_feed_success(client: AsyncClient, auth_headers, db_session):
    """Test successful feed deletion."""
    from models.feed_source import FeedSource

    # Create a test feed
    test_feed = FeedSource(
        name="Test Feed to Delete",
        feed_url="https://example.com/test.rss",
        enabled=True
    )
    db_session.add(test_feed)
    await db_session.commit()
    await db_session.refresh(test_feed)
    feed_id = test_feed.id

    # Delete the feed
    response = await client.delete(f"/api/feeds/{feed_id}", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "deleted"
    assert data["feed_id"] == feed_id
    assert data["name"] == "Test Feed to Delete"

    # Verify feed is deleted from database
    from sqlalchemy import select
    result = await db_session.execute(
        select(FeedSource).where(FeedSource.id == feed_id)
    )
    deleted_feed = result.scalar_one_or_none()
    assert deleted_feed is None


@pytest.mark.asyncio
async def test_cannot_delete_with_wrong_credentials(client: AsyncClient):
    """Test that wrong credentials are rejected."""
    wrong_credentials = base64.b64encode(b"wrong:wrong").decode()
    headers = {"Authorization": f"Basic {wrong_credentials}"}

    response = await client.delete("/api/feeds/1", headers=headers)
    assert response.status_code == 401
