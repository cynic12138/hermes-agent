from __future__ import annotations

from ..binding_helpers import bind_fields, feedback


EXECUTION_BINDERS = {
    "record_image_result_feedback": lambda context: bind_fields(context, {"asset": "result_id", "note": "note"}),
    "record_video_result_feedback": lambda context: bind_fields(context, {"asset": "result_id", "note": "note"}),
    "record_video_brief_feedback": lambda context: bind_fields(context, {"note": "note"}),
    "record_channel_feedback": lambda context: bind_fields(context, {"note": "note"}),
}

CONVERSATION_BINDERS = {
    "record_channel_feedback": lambda context: feedback(context, variant=True),
    "record_image_result_feedback": lambda context: feedback(context),
    "record_video_brief_feedback": lambda context: feedback(context),
    "record_video_result_feedback": lambda context: feedback(context),
}
