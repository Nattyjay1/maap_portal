from types import SimpleNamespace

from django.test import SimpleTestCase

from .analytics_utils import (
    HIGH_RISK,
    INCOMPLETE_DATA,
    LOW_RISK,
    MODERATE_RISK,
    NO_DATA,
    calculate_student_risk,
    compute_faculty_submission_progress,
    get_recommended_action,
    get_risk_reason,
)


class AnalyticsUtilsTests(SimpleTestCase):
    def test_calculate_student_risk_uses_expected_thresholds(self):
        self.assertEqual(calculate_student_risk(74.99, 95), HIGH_RISK)
        self.assertEqual(calculate_student_risk(85, 74.99), HIGH_RISK)
        self.assertEqual(calculate_student_risk(75, 95), MODERATE_RISK)
        self.assertEqual(calculate_student_risk(90, 84), MODERATE_RISK)
        self.assertEqual(calculate_student_risk(80, 85), LOW_RISK)

    def test_calculate_student_risk_handles_missing_values(self):
        self.assertEqual(calculate_student_risk(None, None), NO_DATA)
        self.assertEqual(calculate_student_risk(90, None), INCOMPLETE_DATA)
        self.assertEqual(calculate_student_risk(None, 95), INCOMPLETE_DATA)
        self.assertEqual(calculate_student_risk(None, 70), HIGH_RISK)

    def test_risk_reason_and_action_are_safe_for_missing_data(self):
        reason = get_risk_reason(None, None)
        self.assertIn("No grade or attendance", reason)

        action = get_recommended_action(NO_DATA, reason)
        self.assertIn("Request grade and attendance", action)

    def test_compute_faculty_submission_progress_with_iterables(self):
        enrollments = [
            SimpleNamespace(id=1),
            SimpleNamespace(id=2),
            SimpleNamespace(id=3),
        ]
        grades = [
            SimpleNamespace(enrollment_id=1),
            SimpleNamespace(enrollment_id=2),
        ]

        progress = compute_faculty_submission_progress(
            enrollments=enrollments,
            grades=grades,
        )

        self.assertEqual(progress["total_records"], 3)
        self.assertEqual(progress["graded_records"], 2)
        self.assertEqual(progress["missing_records"], 1)
        self.assertEqual(progress["progress_percent"], 66.67)
        self.assertEqual(progress["progress_status"], "In Progress")

    def test_compute_faculty_submission_progress_empty_records(self):
        progress = compute_faculty_submission_progress(enrollments=[], grades=[])

        self.assertEqual(progress["total_records"], 0)
        self.assertEqual(progress["graded_records"], 0)
        self.assertEqual(progress["progress_percent"], 0)
        self.assertEqual(progress["progress_status"], "Not Started")
