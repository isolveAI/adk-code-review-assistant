"""
Centralized state key definitions for the Code Review Assistant.
This ensures consistency across all agents and tools when accessing state.
"""


class StateKeys:
    """State keys used throughout the code review pipeline."""

    # Session-level keys (persist within a session)
    CODE_TO_REVIEW = "code_to_review"
    CODE_ANALYSIS = "code_analysis"
    CODE_LINE_COUNT = "code_line_count"
    STYLE_SCORE = "style_score"
    STYLE_ISSUES = "style_issues"
    STYLE_ISSUE_COUNT = "style_issue_count"
    TEST_RESULTS = "test_results"
    FINAL_GRADE = "final_grade"
    GRADING_ATTEMPTS = "grading_attempts"
    LAST_GRADING_TIME = "last_grading_time"
    SYNTAX_ERROR = "syntax_error"
    PAST_FEEDBACK = "past_feedback"
    FEEDBACK_PATTERNS = "feedback_patterns"
    SCORE_IMPROVEMENT = "score_improvement"

    # Temporary keys (cleared after each invocation)
    TEMP_TEST_CODE = "temp:test_code_to_execute"
    TEMP_ANALYSIS_TIMESTAMP = "temp:analysis_timestamp"
    TEMP_TEST_GENERATION_COMPLETE = "temp:test_generation_complete"
    TEMP_FUNCTIONS_TO_TEST = "temp:functions_to_test"
    TEMP_PROCESSING_TIMESTAMP = "temp:processing_timestamp"

    # User-scoped keys (persist across sessions for a user)
    USER_ID = "user_id"
    USER_PREFERRED_STYLE = "user:preferred_style"
    USER_TOTAL_SUBMISSIONS = "user:total_submissions"
    USER_LAST_STYLE_SCORE = "user:last_style_score"
    USER_LAST_SUBMISSION_TIME = "user:last_submission_time"
    USER_LAST_TEST_PASS_RATE = "user:last_test_pass_rate"
    USER_PAST_FEEDBACK_CACHE = "user:past_feedback_cache"
    USER_LAST_GRADING_REPORT = "user:last_grading_report"

    # App-scoped keys (shared across all users)
    APP_GRADING_VERSION = "app:grading_version"
    APP_STYLE_GUIDE_VERSION = "app:style_guide_version"
