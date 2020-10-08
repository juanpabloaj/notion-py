from copy import deepcopy
from datetime import datetime

from tzlocal import get_localzone


def _normalize_prop_name(prop_name, collection):
    if not prop_name:
        return ""

    return collection.get_schema_property(prop_name).get("id", "")


def _normalize_query_data(data, collection, recursive=False):
    if not recursive:
        data = deepcopy(data)

    if isinstance(data, list):
        return [
            _normalize_query_data(item, collection, recursive=True) for item in data
        ]

    if isinstance(data, dict):
        # convert slugs to property ids
        if "property" in data:
            data["property"] = _normalize_prop_name(data["property"], collection)

        # convert any instantiated objects into their ids
        if "value" in data and hasattr(data["value"], "id"):
            data["value"] = data["value"].id

        for key in data:
            data[key] = _normalize_query_data(data[key], collection, recursive=True)

    return data


class NotionDate:

    start = None
    end = None
    timezone = None
    reminder = None

    def __init__(self, start, end=None, timezone=None, reminder=None):
        self.start = start
        self.end = end
        self.timezone = timezone
        self.reminder = reminder

    @classmethod
    def _parse_datetime(cls, date_str, time_str):
        if not date_str:
            return None
        if time_str:
            return datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H:%M")
        else:
            return datetime.strptime(date_str, "%Y-%m-%d").date()

    def _format_datetime(self, date_or_datetime):
        if not date_or_datetime:
            return None, None
        if isinstance(date_or_datetime, datetime):
            return (
                date_or_datetime.strftime("%Y-%m-%d"),
                date_or_datetime.strftime("%H:%M"),
            )
        else:
            return date_or_datetime.strftime("%Y-%m-%d"), None

    def type(self):
        name = "date"
        if isinstance(self.start, datetime):
            name += "time"
        if self.end:
            name += "range"
        return name

    @classmethod
    def from_notion(cls, obj):
        if isinstance(obj, dict):
            data = obj
        elif isinstance(obj, list):
            data = obj[0][1][0][1]
        else:
            return None
        start = cls._parse_datetime(data.get("start_date"), data.get("start_time"))
        end = cls._parse_datetime(data.get("end_date"), data.get("end_time"))
        timezone = data.get("timezone")
        reminder = data.get("reminder")
        return cls(start, end=end, timezone=timezone, reminder=reminder)

    def to_notion(self):

        if self.end:
            self.start, self.end = sorted([self.start, self.end])

        start_date, start_time = self._format_datetime(self.start)
        end_date, end_time = self._format_datetime(self.end)

        if not start_date:
            return []

        data = {"type": self.type(), "start_date": start_date}

        if end_date:
            data["end_date"] = end_date

        if "time" in data["type"]:
            data["time_zone"] = str(self.timezone or get_localzone())
            data["start_time"] = start_time or "00:00"
            if end_date:
                data["end_time"] = end_time or "00:00"

        if self.reminder:
            data["reminder"] = self.reminder

        return [["‣", [["d", data]]]]
