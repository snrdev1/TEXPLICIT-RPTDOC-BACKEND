import enum
from typing import TypeVar


class Enumerator:
    T = TypeVar("T")

    # The CommentType class is an enumeration that represents different types of comments.
    class CommentType(enum.Enum):
        Review = 1
        Discussion = 2

    # The CommentSortBy class is an enumeration that represents different sorting options for
    # comments.
    class CommentSortBy(enum.Enum):
        TOP_COMMENTS = 1
        LATEST_COMMENTS = 2
        OLDEST_COMMENTS = 3

    # The above class defines an enumeration for the status of a knowledge item.
    class KnowledgeItemStatus(enum.Enum):
        Open = 1
        Approved = 2
        Rejected = 3

    # The DatasourceTypes class is an enumeration that represents different types of data sources.
    class DatasourceTypes(enum.Enum):
        MYSQL = 0
        MSSQL = 1
        POSTGRESQL = 2
        MONGODB = 3

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
        KnowledgeItem = 2
        CustomerService = 3

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

    # The class KiRejectionReason is an enumeration that represents different reasons for rejection.
    class KiRejectionReason(enum.Enum):
        preface = "Our team identified the following issue(s) with your submission: "
        reasons = [
            "It violates Texplicit02's community guidelines or terms of service.",
            "It contains offensive or inappropriate content.",
            "It lacks sufficient relevance or value to the Texplicit02 community.",
            "It has already been submitted by another user.",
            "It is too similar to existing knowledge items on the platform.",
            "It contains inaccurate or misleading information.",
            "It is too promotional in nature.",
            "It contains copyrighted material that the user does not have the right to share.",
            "It is too short or incomplete to provide meaningful value to the community.",
        ]
        suffix = "Comments from the Admin: "

    # MenuItems
    class MenuItems(enum.Enum):
        Home = 0
        MyNetwork = 1
        MyTexplicit = 2
        MyDocuments = 3
        MyDatasources = 4
        News = 5
        AIChat = 6
        UserManagement = 7
        Admin = 8
        Reports = 9