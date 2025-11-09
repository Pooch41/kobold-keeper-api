import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.hashers import check_password
import json

from api.models import User, Group, Character, Roll, RecoveryKey

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    """A standard, unauthenticated API client."""
    return APIClient()


@pytest.fixture
def test_user():
    """Creates a standard user."""
    return User.objects.create_user(username="testuser", password="testpassword123")


@pytest.fixture
def test_user_2():
    """Creates a second user for permission testing."""
    return User.objects.create_user(username="testuser2", password="testpassword123")


@pytest.fixture
def authenticated_client(client, test_user):
    """
    A client that is authenticated using DRF's built-in force_authenticate.
    This bypasses the login endpoint entirely, avoiding any rate-limiting.
    """
    client.force_authenticate(user=test_user)
    return client


@pytest.fixture
def test_group(test_user):
    """A group owned by test_user."""
    return Group.objects.create(group_name="Test Group", owner=test_user)


@pytest.fixture
def test_character(test_user, test_group):
    """A character owned by test_user and in test_group."""
    return Character.objects.create(
        character_name="Test Character",
        group=test_group,
        user=test_user
    )


class TestAuthentication:
    """Tests all public-facing auth endpoints."""

    def test_register_user(self, client):
        """
        Tests the /api/auth/register/ endpoint.
        """
        url = reverse("register")
        data = {
            "username": "newuser",
            "password": "newpassword123"
        }
        response = client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["username"] == "newuser"
        assert "recovery_key" in response.data

        assert User.objects.filter(username="newuser").exists()
        assert RecoveryKey.objects.filter(user__username="newuser").exists()

    def test_login_user(self, client, test_user):
        """
        Tests the /api/auth/token/ (login) endpoint.
        """
        url = reverse("token_obtain_pair")
        data = {
            "username": "testuser",
            "password": "testpassword123"
        }
        response = client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_password_reset_with_key(self, client):
        """
        Tests the entire password reset flow, which we fixed.
        """

        register_url = reverse("register")
        register_data = {"username": "resetuser", "password": "oldpassword123"}
        register_response = client.post(register_url, register_data)
        recovery_key = register_response.data["recovery_key"]

        reset_url = reverse("password_reset_with_key")
        reset_data = {
            "username": "resetuser",
            "recovery_key": recovery_key,
            "new_password": "newpassword123"
        }
        reset_response = client.post(reset_url, reset_data)
        assert reset_response.status_code == status.HTTP_200_OK

        login_url = reverse("token_obtain_pair")
        login_data = {"username": "resetuser", "password": "newpassword123"}
        login_response = client.post(login_url, login_data)
        assert login_response.status_code == status.HTTP_200_OK
        assert "access" in login_response.data


class TestAuthenticatedEndpoints:
    """Tests endpoints that require a user to be logged in."""

    def test_password_change(self, authenticated_client, test_user):
        """
        Tests the /api/auth/password/change/ endpoint.
        """
        url = reverse("password_change")
        data = {
            "old_password": "testpassword123",
            "new_password": "new_secure_password",
            "new_password_confirm": "new_secure_password"
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK

        test_user.refresh_from_db()
        assert check_password("new_secure_password", test_user.password)

    def test_create_and_list_groups(self, authenticated_client, test_user):
        """
        Tests GET and POST on /api/groups/
        """
        url = reverse("group-list")

        data = {"group_name": "My New Campaign"}
        response_post = authenticated_client.post(url, data)
        assert response_post.status_code == status.HTTP_201_CREATED
        assert response_post.data["group_name"] == "My New Campaign"

        created_group = Group.objects.get(id=response_post.data['id'])
        assert created_group.owner == test_user

        response_get = authenticated_client.get(url)
        assert response_get.status_code == status.HTTP_200_OK
        assert len(response_get.data) == 1
        assert response_get.data[0]["group_name"] == "My New Campaign"

    def test_create_and_list_characters(self, authenticated_client, test_group):
        """
        Tests GET and POST on /api/characters/
        Requires a group to exist first.
        """
        url = reverse("character-list")
        data = {
            "character_name": "Grog",
            "group": test_group.id
        }
        response_post = authenticated_client.post(url, data)
        assert response_post.status_code == status.HTTP_201_CREATED
        assert response_post.data["character_name"] == "Grog"

        # Test GET
        response_get = authenticated_client.get(url)
        assert response_get.status_code == status.HTTP_200_OK
        assert len(response_get.data) == 1

    def test_create_and_list_rolls(self, authenticated_client, test_group, test_character):
        """
        Tests GET and POST on /api/rolls/
        """
        url = reverse("roll-list")
        data = {
            "target_character_id": test_character.id,
            "group_id": test_group.id,
            "roll_input": "2d6+5"
        }
        response_post = authenticated_client.post(url, data)
        assert response_post.status_code == status.HTTP_201_CREATED
        assert response_post.data["roll_input_display"] == "2d6+5"

        assert 7 <= response_post.data["roll_value"] <= 17
        assert "luck_index" in response_post.data

        response_get = authenticated_client.get(url)
        assert response_get.status_code == status.HTTP_200_OK
        assert len(response_get.data) == 1
        assert response_get.data[0]["roll_input_display"] == "2d6+5"


class TestPermissions:
    """
    Tests that users can ONLY access their own data.
    This is the most critical security test.
    """

    def test_user_cannot_see_other_users_groups(self, authenticated_client, test_user_2):
        """
        Check that the /api/groups/ list view is properly filtered.
        """
        Group.objects.create(group_name="Secret Group", owner=test_user_2)

        url = reverse("group-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_user_cannot_access_other_users_group_detail(self, authenticated_client, test_user_2):
        """
        Check that /api/groups/<pk>/ returns 404 for other users' groups.
        """
        secret_group = Group.objects.create(group_name="Secret Group", owner=test_user_2)
        url = reverse("group-detail", kwargs={"pk": secret_group.id})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_create_character_in_other_users_group(self, authenticated_client, test_user_2):
        """
        Tests that the CharacterSerializer's group-filtering logic works.
        """
        secret_group = Group.objects.create(group_name="Secret Group", owner=test_user_2)
        url = reverse("character-list")

        data = {
            "character_name": "Intruder",
            "group": secret_group.id
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAnalytics:
    """
    Tests the analytics endpoints.
    """


    @pytest.fixture
    def lucky_roll_json(self):
        return json.dumps([
            {"rolls": [20], "total": 20, "formula": "1d20", "component_type": "dice"}
        ])

    @pytest.fixture
    def unlucky_roll_json(self):
        return json.dumps([
            {"rolls": [1], "total": 1, "formula": "1d20", "component_type": "dice"}
        ])

    def test_luck_analytics_with_data(self, authenticated_client, test_group, test_character, lucky_roll_json):
        """
        Tests the /api/analytics/luck/ endpoint.
        """
        Roll.objects.create(
            character=test_character,
            group=test_group,
            roll_input="1d20",
            roll_value=20,
            luck_index=1.0,
            raw_dice_rolls=lucky_roll_json
        )

        url = reverse("luck-analytics")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "statistics" in response.data
        assert response.data["statistics"]["total_rolls"] == 1
        assert response.data["statistics"]["avg_modified_roll"] == 20.0

    def test_luckiest_roller(self, authenticated_client, test_user, test_group, test_character, lucky_roll_json,
                             unlucky_roll_json):
        """
        Tests the /api/analytics/luckiest-roller/ endpoint.
        The function needs at least two characters to compare.
        """
        unlucky_character = Character.objects.create(
            character_name="Unlucky Bob",
            group=test_group,
            user=test_user
        )

        for _ in range(15):
            Roll.objects.create(
                character=test_character,
                group=test_group,
                roll_input="1d20",
                roll_value=20,
                luck_index=1.0,
                raw_dice_rolls=lucky_roll_json
            )


        for _ in range(15):
            Roll.objects.create(
                character=unlucky_character,
                group=test_group,
                roll_input="1d20",
                roll_value=1,
                luck_index=-1.0,
                raw_dice_rolls=unlucky_roll_json
            )

        url = reverse("luckiest-roller")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "luckiest_roller" in response.data
        assert response.data["luckiest_roller"]["character_name"] == "Test Character"
