from rest_framework import serializers

from .models import DuplicateFlag
from .models import Report
from .models import ReportStatus


class ReportStatusSerializer(serializers.ModelSerializer):
    """Serializer for ReportStatus model."""

    class Meta:
        model = ReportStatus
        fields = "__all__"
        read_only_fields = ["created_at"]


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model."""

    class Meta:
        model = Report
        fields = "__all__"
        read_only_fields = ["submitted_at"]

    def validate(self, data):
        errors = {}

        # for partial updates some fields may not be in data,
        # so fall back to the existing instance value if there is one
        instance = self.instance
        case_count = data.get("case_count", getattr(instance, "case_count", 0))
        death_count = data.get("death_count", getattr(instance, "death_count", 0))

        # deaths cannot exceed total cases
        if death_count > case_count:
            errors["death_count"] = "Deaths cannot exceed the total case count."

        # check sex breakdown only when the user provided some counts
        male = data.get("male_count", getattr(instance, "male_count", 0))
        female = data.get("female_count", getattr(instance, "female_count", 0))
        unknown_sex = data.get("unknown_sex_count", getattr(instance, "unknown_sex_count", 0))
        sex_total = male + female + unknown_sex
        if sex_total > 0 and sex_total != case_count:
            errors["male_count"] = (
                "Sex breakdown counts must add up to the total case count."
            )

        # check age breakdown only when the user provided some counts
        age_u5 = data.get("age_under5_count", getattr(instance, "age_under5_count", 0))
        age_517 = data.get("age_5_17_count", getattr(instance, "age_5_17_count", 0))
        age_1859 = data.get("age_18_59_count", getattr(instance, "age_18_59_count", 0))
        age_60p = data.get("age_60plus_count", getattr(instance, "age_60plus_count", 0))
        unknown_age = data.get("unknown_age_count", getattr(instance, "unknown_age_count", 0))
        age_total = age_u5 + age_517 + age_1859 + age_60p + unknown_age
        if age_total > 0 and age_total != case_count:
            errors["age_under5_count"] = (
                "Age breakdown counts must add up to the total case count."
            )

        # prevent changing a submitted report back to draft via the API
        if instance is not None:
            new_status = data.get("status")
            if new_status is not None:
                current_status_name = instance.status.status_name
                if current_status_name != "DRAFT" and new_status.status_name == "DRAFT":
                    errors["status"] = (
                        "A report that has already been submitted cannot be changed back to draft."
                    )

        if errors:
            raise serializers.ValidationError(errors)

        return data


class DuplicateFlagSerializer(serializers.ModelSerializer):
    """Serializer for DuplicateFlag model."""

    class Meta:
        model = DuplicateFlag
        fields = "__all__"
        read_only_fields = ["flagged_at"]

    def validate(self, data):
        instance = self.instance

        # fall back to existing values for partial updates
        reviewed_by = data.get("reviewed_by", getattr(instance, "reviewed_by", None))
        review_outcome = data.get("review_outcome", getattr(instance, "review_outcome", None))
        reviewed_at = data.get("reviewed_at", getattr(instance, "reviewed_at", None))

        # all three review fields must be set together or all left empty
        any_set = bool(reviewed_by) or bool(review_outcome) or bool(reviewed_at)
        all_set = bool(reviewed_by) and bool(review_outcome) and bool(reviewed_at)
        if any_set and not all_set:
            raise serializers.ValidationError(
                "reviewed_by, review_outcome, and reviewed_at must all be set together."
            )

        return data

