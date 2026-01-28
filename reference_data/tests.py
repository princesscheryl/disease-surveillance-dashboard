from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from reference_data.models import Disease, Location


User = get_user_model()


def _build_payload_for_model(model_cls):
    """
    Build a minimal valid payload for POSTing to a ModelViewSet without
    hardcoding field names.

    Rules:
    - Skip auto fields (id, created_at auto_now_add, etc.)
    - Skip relations (FK/M2M) unless required (we'll leave them out for now)
    - For required non-relational fields, provide a sensible dummy value
    """
    payload = {}
    for field in model_cls._meta.get_fields():
        # We only want concrete DB fields, not reverse relations
        if not hasattr(field, "attname"):
            continue

        # Skip PK / auto-created fields
        if getattr(field, "primary_key", False):
            continue
        if getattr(field, "auto_created", False):
            continue

        # Skip relations (FK/M2M/O2O) for now
        if field.is_relation:
            continue

        # If the field has a default OR is nullable/blank, we can skip it safely
        has_default = field.has_default()
        if has_default or getattr(field, "null", False) or getattr(field, "blank", False):
            continue

        # Now it's a required scalar field — we must fill it
        # Choose a value based on field type
        internal_type = field.get_internal_type()

        if internal_type in ("CharField", "TextField", "SlugField", "EmailField", "URLField"):
            payload[field.name] = "Test Value"
        elif internal_type in ("IntegerField", "BigIntegerField", "SmallIntegerField", "PositiveIntegerField", "PositiveSmallIntegerField"):
            payload[field.name] = 1
        elif internal_type in ("BooleanField",):
            payload[field.name] = True
        elif internal_type in ("FloatField", "DecimalField"):
            payload[field.name] = 1.0
        elif internal_type in ("DateField",):
            payload[field.name] = "2026-01-01"
        elif internal_type in ("DateTimeField",):
            payload[field.name] = "2026-01-01T00:00:00Z"
        else:
            # Fallback: try string
            payload[field.name] = "Test Value"

    return payload


class DiseaseTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Your project uses email-based login (no username), so create a user this way
        self.user = User.objects.create_user(
            email="tester@example.com",
            password="testpass123",
        )

        # Most cookiecutter setups protect the API by default, so authenticate the client
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("api:disease-list")

    def test_list_diseases(self):
        # Create one object directly in the DB to ensure GET returns something
        Disease.objects.create(**_build_payload_for_model(Disease))
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_disease(self):
        payload = _build_payload_for_model(Disease)
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unique_constraint_if_any(self):
        """
        If the Disease model has any unique fields, posting a duplicate should fail (usually 400).
        If it has no unique fields, we skip the assertion.
        """
        payload = _build_payload_for_model(Disease)

        # Detect unique scalar fields we included in the payload
        unique_fields = []
        for field in Disease._meta.fields:
            if field.name in payload and getattr(field, "unique", False):
                unique_fields.append(field.name)

        # If there are no unique fields in the payload, we can't reliably test duplicates.
        if not unique_fields:
            self.skipTest("Disease model has no unique fields in the required payload; skipping duplicate test.")

        # First create should work
        r1 = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)

        # Second create with same unique values should fail
        r2 = self.client.post(self.list_url, payload, format="json")
        self.assertIn(r2.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT))


class LocationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Create a test user
        self.user = User.objects.create_user(
            email="location_tester@example.com",
            password="testpass123",
        )

        # Authenticate the client
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("api:location-list")

    def test_create_location(self):
        payload = _build_payload_for_model(Location)
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_locations(self):
        # Create one location to ensure GET returns something
        Location.objects.create(**_build_payload_for_model(Location))
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_area_name_can_be_null(self):
        payload = {"district_name": "Test District"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data.get("area_name"))



def _build_payload_for_model(model_cls):
    """
    Build a minimal valid payload for POSTing to a ModelViewSet without
    hardcoding field names.

    Rules:
    - Skip auto fields (id, created_at auto_now_add, etc.)
    - Skip relations (FK/M2M) unless required (we’ll leave them out for now)
    - For required non-relational fields, provide a sensible dummy value
    """
    payload = {}
    for field in model_cls._meta.get_fields():
        # We only want concrete DB fields, not reverse relations
        if not hasattr(field, "attname"):
            continue

        # Skip PK / auto-created fields
        if getattr(field, "primary_key", False):
            continue
        if getattr(field, "auto_created", False):
            continue

        # Skip relations (FK/M2M/O2O) for now
        if field.is_relation:
            continue

        # If the field has a default OR is nullable/blank, we can skip it safely
        has_default = field.has_default()
        if has_default or getattr(field, "null", False) or getattr(field, "blank", False):
            continue

        # Now it’s a required scalar field — we must fill it
        # Choose a value based on field type
        internal_type = field.get_internal_type()

        if internal_type in ("CharField", "TextField", "SlugField", "EmailField", "URLField"):
            payload[field.name] = "Test Value"
        elif internal_type in ("IntegerField", "BigIntegerField", "SmallIntegerField", "PositiveIntegerField", "PositiveSmallIntegerField"):
            payload[field.name] = 1
        elif internal_type in ("BooleanField",):
            payload[field.name] = True
        elif internal_type in ("FloatField", "DecimalField"):
            payload[field.name] = 1.0
        elif internal_type in ("DateField",):
            payload[field.name] = "2026-01-01"
        elif internal_type in ("DateTimeField",):
            payload[field.name] = "2026-01-01T00:00:00Z"
        else:
            # Fallback: try string
            payload[field.name] = "Test Value"

    return payload


class DiseaseTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Your project uses email-based login (no username), so create a user this way
        self.user = User.objects.create_user(
            email="tester@example.com",
            password="testpass123",
        )

        # Most cookiecutter setups protect the API by default, so authenticate the client
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("api:disease-list")

    def test_list_diseases(self):
        # Create one object directly in the DB to ensure GET returns something
        Disease.objects.create(**_build_payload_for_model(Disease))
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_disease(self):
        payload = _build_payload_for_model(Disease)
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unique_constraint_if_any(self):
        """
        If the Disease model has any unique fields, posting a duplicate should fail (usually 400).
        If it has no unique fields, we skip the assertion.
        """
        payload = _build_payload_for_model(Disease)

        # Detect unique scalar fields we included in the payload
        unique_fields = []
        for field in Disease._meta.fields:
            if field.name in payload and getattr(field, "unique", False):
                unique_fields.append(field.name)

        # If there are no unique fields in the payload, we can’t reliably test duplicates.
        if not unique_fields:
            self.skipTest("Disease model has no unique fields in the required payload; skipping duplicate test.")

        # First create should work
        r1 = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)

        # Second create with same unique values should fail
        r2 = self.client.post(self.list_url, payload, format="json")
        self.assertIn(r2.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT))