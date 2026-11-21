"""Add the CRM and Sales dashboards on sites that had the app before they existed."""

from ric_template.dashboards.setup import install_dashboards


def execute():
    install_dashboards()
