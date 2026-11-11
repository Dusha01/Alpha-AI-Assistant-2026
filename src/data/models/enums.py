from enum import StrEnum


class BusinessStage(StrEnum):
    PLANNING = "planning"
    LT_YEAR = "lt_year"
    GT_YEAR = "gt_year"


class TaxMode(StrEnum):
    USN = "usn"
    PATENT = "patent"
    NPD = "npd"
    OTHER = "other"
    UNKNOWN = "unknown"
