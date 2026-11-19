"""The package's default roles, as roles declared in code (#94): same five groups, same
permissions as before, now through whiteneuron.base.roles.sync_roles (run it again at any time:
each group is set back to exactly these permissions)."""
from django.core.management.base import BaseCommand

from whiteneuron.base.roles import Role, sync_roles

# Kept for projects that import them
GROUP = {
    'admin': 'Quản trị viên',
    'manager': 'Quản lý',
    'staff': 'Nhân viên',
    'customer': 'Khách hàng',
    'guest': 'Khách thăm',
}

# codename__icontains, as the command always matched: custom permissions included
_PRIVATE = ("user", "useractivity", "group", "permission", "contenttype", "logentry",
            "session", "token", "authtoken")

DEFAULT_ROLES = [
    Role(key="admin", group_name=GROUP["admin"], permissions=("*view*", "*add*", "*change*", "*delete*")),
    Role(key="manager", group_name=GROUP["manager"], permissions=("*view*", "*add*", "*change*")),
    Role(key="staff", group_name=GROUP["staff"], permissions=("*view*",), exclude=_PRIVATE),
    Role(key="customer", group_name=GROUP["customer"], permissions=("*view*",), exclude=_PRIVATE),
    Role(key="guest", group_name=GROUP["guest"], permissions=("*view*",),
         exclude=_PRIVATE + ("excelfile", "pdffile")),
]


def init_group(stdout=None):
    return sync_roles(DEFAULT_ROLES, stdout=stdout)


class Command(BaseCommand):
    help = "Create the package's default role groups and set their permissions"

    def handle(self, *args, **kwargs):
        init_group(stdout=self.stdout)
        self.stdout.write("Done")
