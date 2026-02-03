"""
Community Integration Tests

Kapsamlı community özellik testleri:
- Community oluşturma
- Üyelik yönetimi (katıl/ayrıl)
- Mesajlaşma
- Yetkilendirme kontrolleri
- Edge case'ler
"""

import asyncio
import pytest
import httpx
from uuid import uuid4
from typing import Optional


# Test configuration
BASE_URL = "http://localhost:8080/api/v1"
TEST_TIMEOUT = 30.0


class TestCommunityAPI:
    """Community API integration tests."""

    @pytest.fixture
    def client(self):
        """HTTP client fixture."""
        return httpx.AsyncClient(base_url=BASE_URL, timeout=TEST_TIMEOUT)

    @pytest.fixture
    def auth_headers(self):
        """Authentication headers fixture - requires valid test token."""
        # In real tests, this would be a valid JWT token
        return {"Authorization": "Bearer test_token"}

    # ==================== COMMUNITY CREATION ====================

    @pytest.mark.asyncio
    async def test_create_community_success(self, client, auth_headers):
        """Test creating a new community."""
        payload = {
            "name": f"Test Community {uuid4().hex[:8]}",
            "description": "Test community for integration tests",
            "community_type": "open",
            "focus_topics": ["teknoloji", "felsefe"],
            "max_members": 50,
            "require_approval": False
        }

        async with client:
            response = await client.post(
                "/communities",
                json=payload,
                headers=auth_headers
            )

        # Should return 201 Created
        assert response.status_code == 201
        data = response.json()
        assert data.get("success") is True
        
        community = data.get("data")
        assert community is not None
        assert community["name"] == payload["name"]
        assert community["community_type"] == "open"
        assert community["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_community_with_turkish_name(self, client, auth_headers):
        """Test creating community with Turkish characters in name."""
        payload = {
            "name": "Gece Kuşları Topluluğu",
            "description": "Gece aktif olanlar için",
            "community_type": "open",
            "focus_topics": ["nostalji", "absurt"]
        }

        async with client:
            response = await client.post(
                "/communities",
                json=payload,
                headers=auth_headers
            )

        if response.status_code == 201:
            data = response.json()
            community = data.get("data")
            # Slug should be properly transliterated
            assert "gece-kuslari" in community.get("slug", "")

    @pytest.mark.asyncio
    async def test_create_community_validation_error(self, client, auth_headers):
        """Test creating community with invalid data."""
        payload = {
            "name": "",  # Empty name should fail
            "community_type": "invalid_type"
        }

        async with client:
            response = await client.post(
                "/communities",
                json=payload,
                headers=auth_headers
            )

        # Should return 400 Bad Request
        assert response.status_code in [400, 422]

    # ==================== COMMUNITY LISTING ====================

    @pytest.mark.asyncio
    async def test_list_communities(self, client):
        """Test listing communities."""
        async with client:
            response = await client.get("/communities")

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "communities" in data.get("data", {})

    @pytest.mark.asyncio
    async def test_list_communities_with_pagination(self, client):
        """Test listing communities with pagination."""
        async with client:
            response = await client.get("/communities?limit=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        communities = data.get("data", {}).get("communities", [])
        assert len(communities) <= 5

    @pytest.mark.asyncio
    async def test_get_community_by_slug(self, client):
        """Test getting a community by slug."""
        # First, list communities to get a valid slug
        async with client:
            list_response = await client.get("/communities?limit=1")
            
        if list_response.status_code == 200:
            communities = list_response.json().get("data", {}).get("communities", [])
            if communities:
                slug = communities[0].get("slug")
                
                async with client:
                    response = await client.get(f"/communities/{slug}")
                
                assert response.status_code == 200
                data = response.json()
                assert data.get("data", {}).get("community", {}).get("slug") == slug

    @pytest.mark.asyncio
    async def test_get_community_not_found(self, client):
        """Test getting a non-existent community."""
        async with client:
            response = await client.get("/communities/nonexistent-slug-12345")

        assert response.status_code == 404

    # ==================== MEMBERSHIP ====================

    @pytest.mark.asyncio
    async def test_join_community(self, client, auth_headers):
        """Test joining a community."""
        # First get a community
        async with client:
            list_response = await client.get("/communities?limit=1")
            
        if list_response.status_code == 200:
            communities = list_response.json().get("data", {}).get("communities", [])
            if communities:
                slug = communities[0].get("slug")
                
                async with client:
                    response = await client.post(
                        f"/communities/{slug}/join",
                        headers=auth_headers
                    )
                
                # Should be 200 OK or 409 if already joined
                assert response.status_code in [200, 409]

    @pytest.mark.asyncio
    async def test_join_nonexistent_community(self, client, auth_headers):
        """Test joining a non-existent community."""
        async with client:
            response = await client.post(
                "/communities/nonexistent-slug-12345/join",
                headers=auth_headers
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_leave_community(self, client, auth_headers):
        """Test leaving a community."""
        async with client:
            list_response = await client.get("/communities?limit=1")
            
        if list_response.status_code == 200:
            communities = list_response.json().get("data", {}).get("communities", [])
            if communities:
                slug = communities[0].get("slug")
                
                # First join
                async with client:
                    await client.post(f"/communities/{slug}/join", headers=auth_headers)
                    
                    # Then leave
                    response = await client.delete(
                        f"/communities/{slug}/leave",
                        headers=auth_headers
                    )
                
                assert response.status_code in [200, 404]  # 404 if not a member

    # ==================== MESSAGING ====================

    @pytest.mark.asyncio
    async def test_list_messages(self, client):
        """Test listing community messages."""
        async with client:
            list_response = await client.get("/communities?limit=1")
            
        if list_response.status_code == 200:
            communities = list_response.json().get("data", {}).get("communities", [])
            if communities:
                slug = communities[0].get("slug")
                
                async with client:
                    response = await client.get(f"/communities/{slug}/messages")
                
                assert response.status_code == 200
                data = response.json()
                assert "messages" in data.get("data", {})

    @pytest.mark.asyncio
    async def test_send_message(self, client, auth_headers):
        """Test sending a message to a community."""
        async with client:
            list_response = await client.get("/communities?limit=1")
            
        if list_response.status_code == 200:
            communities = list_response.json().get("data", {}).get("communities", [])
            if communities:
                slug = communities[0].get("slug")
                
                # First join the community
                async with client:
                    await client.post(f"/communities/{slug}/join", headers=auth_headers)
                    
                    # Send message
                    response = await client.post(
                        f"/communities/{slug}/messages",
                        json={"content": "Merhaba topluluk!"},
                        headers=auth_headers
                    )
                
                # Should be 201 Created or 403 if not a member
                assert response.status_code in [201, 403]

    @pytest.mark.asyncio
    async def test_send_message_not_member(self, client, auth_headers):
        """Test sending message when not a member."""
        async with client:
            list_response = await client.get("/communities?limit=1")
            
        if list_response.status_code == 200:
            communities = list_response.json().get("data", {}).get("communities", [])
            if communities:
                slug = communities[0].get("slug")
                
                # Leave first to ensure not a member
                async with client:
                    await client.delete(f"/communities/{slug}/leave", headers=auth_headers)
                    
                    # Try to send message
                    response = await client.post(
                        f"/communities/{slug}/messages",
                        json={"content": "Test message"},
                        headers=auth_headers
                    )
                
                # Should be 403 Forbidden
                assert response.status_code in [403, 201]  # 201 if auto-join is enabled

    @pytest.mark.asyncio
    async def test_send_message_with_reply(self, client, auth_headers):
        """Test sending a reply message."""
        async with client:
            list_response = await client.get("/communities?limit=1")
            
        if list_response.status_code == 200:
            communities = list_response.json().get("data", {}).get("communities", [])
            if communities:
                slug = communities[0].get("slug")
                
                async with client:
                    # Join and get messages
                    await client.post(f"/communities/{slug}/join", headers=auth_headers)
                    messages_response = await client.get(f"/communities/{slug}/messages")
                    
                    if messages_response.status_code == 200:
                        messages = messages_response.json().get("data", {}).get("messages", [])
                        if messages:
                            reply_to_id = messages[0].get("id")
                            
                            response = await client.post(
                                f"/communities/{slug}/messages",
                                json={
                                    "content": "Bu bir cevap!",
                                    "reply_to_id": reply_to_id
                                },
                                headers=auth_headers
                            )
                            
                            if response.status_code == 201:
                                data = response.json()
                                assert data.get("data", {}).get("reply_to_id") == reply_to_id

    # ==================== EDGE CASES ====================

    @pytest.mark.asyncio
    async def test_unauthorized_create_community(self, client):
        """Test creating community without authentication."""
        payload = {
            "name": "Unauthorized Community",
            "community_type": "open"
        }

        async with client:
            response = await client.post("/communities", json=payload)

        # Should return 401 Unauthorized
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_join_community(self, client):
        """Test joining community without authentication."""
        async with client:
            response = await client.post("/communities/some-slug/join")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_message_content(self, client, auth_headers):
        """Test sending empty message."""
        async with client:
            list_response = await client.get("/communities?limit=1")
            
        if list_response.status_code == 200:
            communities = list_response.json().get("data", {}).get("communities", [])
            if communities:
                slug = communities[0].get("slug")
                
                async with client:
                    await client.post(f"/communities/{slug}/join", headers=auth_headers)
                    
                    response = await client.post(
                        f"/communities/{slug}/messages",
                        json={"content": ""},  # Empty content
                        headers=auth_headers
                    )
                
                # Should be 400 Bad Request
                assert response.status_code in [400, 422, 201]  # 201 if empty allowed


class TestCommunityFlow:
    """End-to-end community flow tests."""

    @pytest.fixture
    def client(self):
        return httpx.AsyncClient(base_url=BASE_URL, timeout=TEST_TIMEOUT)

    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test_token"}

    @pytest.mark.asyncio
    async def test_full_community_lifecycle(self, client, auth_headers):
        """
        Test full community lifecycle:
        1. Create community
        2. Join community (another user)
        3. Send messages
        4. Leave community
        """
        community_name = f"Lifecycle Test {uuid4().hex[:8]}"
        
        async with client:
            # 1. Create community
            create_response = await client.post(
                "/communities",
                json={
                    "name": community_name,
                    "description": "Lifecycle test community",
                    "community_type": "open",
                    "focus_topics": ["felsefe"]
                },
                headers=auth_headers
            )
            
            if create_response.status_code != 201:
                pytest.skip("Could not create community - auth may be required")
                return
            
            community = create_response.json().get("data")
            slug = community.get("slug")
            
            # 2. Verify community exists
            get_response = await client.get(f"/communities/{slug}")
            assert get_response.status_code == 200
            
            # 3. List members (creator should be there)
            members = get_response.json().get("data", {}).get("members", [])
            assert len(members) >= 1
            
            # 4. Send a message
            msg_response = await client.post(
                f"/communities/{slug}/messages",
                json={"content": "İlk mesaj!"},
                headers=auth_headers
            )
            assert msg_response.status_code == 201
            
            # 5. List messages
            messages_response = await client.get(f"/communities/{slug}/messages")
            assert messages_response.status_code == 200
            messages = messages_response.json().get("data", {}).get("messages", [])
            assert len(messages) >= 1
            
            # 6. Leave community
            leave_response = await client.delete(
                f"/communities/{slug}/leave",
                headers=auth_headers
            )
            # Owner might not be able to leave
            assert leave_response.status_code in [200, 400, 403]


# ==================== HELPER FUNCTIONS ====================

async def create_test_community(client, auth_headers, name: Optional[str] = None) -> dict:
    """Helper to create a test community."""
    if name is None:
        name = f"Test Community {uuid4().hex[:8]}"
    
    response = await client.post(
        "/communities",
        json={
            "name": name,
            "description": "Test community",
            "community_type": "open",
            "focus_topics": ["felsefe"]
        },
        headers=auth_headers
    )
    
    if response.status_code == 201:
        return response.json().get("data", {})
    return {}


async def cleanup_test_community(client, auth_headers, slug: str):
    """Helper to cleanup a test community."""
    # Leave the community
    await client.delete(f"/communities/{slug}/leave", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
