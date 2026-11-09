from enum import StrEnum


class Command(StrEnum):
    START = "start"
    HELP = "help"

    VIEW_ENDPOINTS = "view_endpoints"
    START_ENDPOINTS = "start_endpoints"
    STOP_ENDPOINTS = "stop_endpoints"
