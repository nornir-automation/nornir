from colorama import Fore, Style


def print_title(title):
    """
    Helper function to print a title.
    """
    msg = "**** {} ".format(title)
    print("{}{}{}{}".format(Style.BRIGHT, Fore.GREEN, msg, "*" * (80 - len(msg))))
