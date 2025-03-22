# Copyright (c) 2024, Applied Relevance, LLC and contributors
# For license information, please see license.txt

import logging
import frappe
from typing import Optional


class EpinomyLogger(logging.Logger):
    """
    A custom logger class for the Epinomy application that extends the standard logging.Logger.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self._setup_logger()

    def _setup_logger(self) -> None:
        """
        Set up and configure the logger.
        """
        self.setLevel(logging.INFO)

        # Remove existing handlers
        for handler in self.handlers[:]:
            self.removeHandler(handler)

        # Add a StreamHandler with a custom formatter
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.addHandler(handler)

    def exception(self, msg: str, *args, exc_info: bool = True, **kwargs) -> None:
        """
        Log an exception with a custom message and additional Frappe logging.
        """
        super().exception(msg, *args, exc_info=exc_info, **kwargs)

        error_message = f"{self.name} {msg}"
        print(error_message)  # Consider removing this in production

        # Truncate the error message for Frappe's log_error function
        truncated_message = error_message[:140]
        frappe.log_error(truncated_message)

    @classmethod
    def get_logger(cls, module_name: str) -> 'EpinomyLogger':
        """
        Get or create an EpinomyLogger instance for the given module name.

        Args:
            module_name (str): The name of the module requesting the logger

        Returns:
            EpinomyLogger: A configured logger instance
        """
        return cls(f"Epinomy {module_name}")


def get_logger(module_name: str) -> EpinomyLogger:
    """
    Get or create an EpinomyLogger instance for the given module name.
    This is a convenience function for backward compatibility.

    Args:
        module_name (str): The name of the module requesting the logger

    Returns:
        EpinomyLogger: A configured logger instance
    """
    return EpinomyLogger.get_logger(module_name)


def add_timeline_entry(document, message: str) -> Optional[str]:
    """
    Adds a simplified comment to the specified document's timeline.

    Args:
        document: The document to which the comment will be added (Document instance)
        message: The content of the comment (str)

    Returns:
        Optional[str]: Name of created comment or None if operation fails
    """
    try:
        doc = frappe.get_doc(document.doctype, document.name)
        comment = frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "content": message,
        })
        comment.insert(ignore_permissions=True)
        return comment.name
    except frappe.DoesNotExistError:
        logger = get_logger(__name__)
        logger.error(
            f"Document {document.doctype} with name {document.name} does not exist.")
        return None
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"An error occurred while adding a timeline entry: {e}")
        return None


def add_timeline_entry_detailed(
    doctype: str,
    docname: str,
    comment_type: str,
    text: str,
    comment_email: Optional[str] = None
) -> Optional[str]:
    """
    Adds a detailed comment to a document's timeline with additional options.

    Args:
        doctype: The Doctype of the document
        docname: The name of the document
        comment_type: Type of the comment ('Comment', 'Info', 'Warning', etc.)
        text: The text content of the comment
        comment_email: The email of the user making the comment. Defaults to current user.

    Returns:
        Optional[str]: The name of the created comment or None if operation fails
    """
    try:
        comment = frappe.get_doc({
            "doctype": "Comment",
            "comment_type": comment_type,
            "reference_doctype": doctype,
            "reference_name": docname,
            "content": text,
            "comment_email": comment_email or frappe.session.user,
        })
        comment.insert(ignore_permissions=True)
        return comment.name
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error adding detailed timeline entry: {str(e)}")
        return None
