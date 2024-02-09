import enum
from typing import TypeVar


class Enumerator:
    T = TypeVar("T")

    # The Role class is an enumeration that represents different roles.
    class Role(enum.Enum):
        Admin = 1
        Professional = 2
        Personal = 3
        Child = 4

    # The UserStatus class is an enumeration that represents different statuses for a user.
    class UserStatus(enum.Enum):
        Active = 1
        Deactive = 2
        Blocked = 3

    # The `ChatType` class is an enumeration that represents different types of chat messages.
    class ChatType(enum.Enum):
        External = 0
        Document = 1

    def convert_to_list(T):
        """
        The function "convert_to_list" takes a list of objects and converts each object into a
        dictionary with "id" and "value" keys, where the "id" is the integer value of the object and the
        "value" is the name of the object with underscores replaced by spaces.

        Args:
          T: T is a parameter that represents a collection of objects.

        Returns:
          The function `convert_to_list` returns a list of dictionaries. Each dictionary in the list has
        two key-value pairs: "id" and "value". The "id" key corresponds to the integer value of
        `x.value`, and the "value" key corresponds to the name of `x` with underscores replaced by
        spaces.
        """
        result = []
        for x in T:
            result.append({"id": int(x.value), "value": x.name.replace("_", " ")})

        return result

    def name(T, value):
        """
        The function "name" takes a type T and a value as input, and returns the name of the value if it
        exists, otherwise it returns "Not Available".

        Args:
          T: T is the type of object that we want to get the name of. It should be a class or an enum
        type that has a name attribute.
          value: The value parameter is the input value that will be converted to a specific type T.

        Returns:
          the name of the value if it exists in the T enum, with underscores replaced by spaces. If the
        value does not exist in the enum or if an exception occurs, the function returns "Not
        Available".
        """
        try:
            result = T(value).name.replace("_", " ")
            return result
        except Exception:
            return "Not Available"

    # MenuItems
    # The class `MenuItems` is an enumeration that represents different menu items.
    class MenuItems(enum.Enum):
        Home = 0
        MyDocuments = 1
        Reports = 2
        UserManagement = 3
        Admin = 4

    # The class "ReportStep" is an enumeration that represents different steps in a report.
    class ReportStep(enum.Enum):
        Pending = 0
        Success = 1
        Failure = 2