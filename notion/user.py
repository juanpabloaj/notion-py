from notion.maps import field_map
from notion.record import Record


class NotionUser(Record):
    """
    Representation of a Notion user.
    """

    _table = "notion_user"
    _str_fields = "email", "full_name"

    user_id = field_map("user_id")
    given_name = field_map("given_name")
    family_name = field_map("family_name")
    email = field_map("email")
    locale = field_map("locale")
    time_zone = field_map("time_zone")

    @property
    def full_name(self) -> str:
        """
        Get full user name.


        Returns
        -------
        str
            User name.
        """
        given = self.given_name or ""
        family = self.family_name or ""
        return f"{given} {family}".strip()
