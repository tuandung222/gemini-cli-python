from enum import Enum


class ApprovalMode(str, Enum):
    DEFAULT = "default"
    AUTO_EDIT = "autoEdit"
    YOLO = "yolo"
    PLAN = "plan"

