"""Installs the CRM and Sales dashboards.

Creates, only when missing (nothing existing is overwritten):

* the two Custom HTML Blocks (CRM KPI Dashboard, Sales Dashboard)
* a "CRM Workspace" workspace that shows the CRM dashboard, with its sidebar entry and
  desktop icon on Frappe versions that have Workspace Sidebar / Desktop Icon
* the Sales Dashboard block at the top of the standard "Selling" workspace
"""

import json
import os

import frappe

BLOCKS_DIR = os.path.join(os.path.dirname(__file__), "blocks")
CRM_WORKSPACE = "CRM Workspace"
CRM_BLOCK = "CRM KPI Dashboard"
SALES_BLOCK = "Sales Dashboard"
CRM_WORKSPACE_ROLES = ["Administrator", "System Manager", "Sales Manager", "Sales User", "Pre Sales"]


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _existing_roles(roles):
    return [{"role": role} for role in roles if frappe.db.exists("Role", role)]


def create_blocks():
    """Create the Custom HTML Blocks from ``blocks/``. Returns the names created."""
    created = []
    for entry in json.loads(_read(os.path.join(BLOCKS_DIR, "index.json"))):
        if frappe.db.exists("Custom HTML Block", entry["name"]):
            continue

        folder = os.path.join(BLOCKS_DIR, entry["dir"])
        frappe.get_doc(
            {
                "doctype": "Custom HTML Block",
                "name": entry["name"],
                "private": 0,
                "html": _read(os.path.join(folder, "block.html")),
                "script": _read(os.path.join(folder, "block.js")),
                "style": _read(os.path.join(folder, "block.css")),
                "roles": _existing_roles(entry["roles"]),
            }
        ).insert(ignore_permissions=True)
        created.append(entry["name"])

    return created


def create_crm_workspace():
    """Create the CRM Workspace, its sidebar entry and its desktop icon."""
    done = []

    if not frappe.db.exists("Workspace", CRM_WORKSPACE):
        content = [
            {
                "id": "crmHeader",
                "type": "header",
                "data": {"text": '<span class="h4"><b>CRM Dashboard</b></span>', "col": 12},
            },
            {
                "id": "crmKpiBlock",
                "type": "custom_block",
                "data": {"custom_block_name": CRM_BLOCK, "col": 12},
            },
        ]
        module = "CRM" if frappe.db.exists("Module Def", "CRM") else "RIC Template"
        frappe.get_doc(
            {
                "doctype": "Workspace",
                "name": CRM_WORKSPACE,
                "label": CRM_WORKSPACE,
                "title": CRM_WORKSPACE,
                "module": module,
                "icon": "crm",
                "type": "Workspace",
                "public": 1,
                "is_hidden": 0,
                "indicator_color": "green",
                "content": json.dumps(content),
                "custom_blocks": [{"custom_block_name": CRM_BLOCK, "label": CRM_BLOCK}],
                "roles": _existing_roles(CRM_WORKSPACE_ROLES),
            }
        ).insert(ignore_permissions=True)
        done.append("CRM Workspace")

    # Newer Frappe versions (v16) also need a sidebar entry and a desktop icon.
    if frappe.db.exists("DocType", "Workspace Sidebar") and not frappe.db.exists("Workspace Sidebar", CRM_WORKSPACE):
        frappe.get_doc(
            {
                "doctype": "Workspace Sidebar",
                "title": CRM_WORKSPACE,
                "header_icon": "crm",
                "standard": 0,
                "items": [
                    {
                        "label": CRM_WORKSPACE,
                        "link_type": "Workspace",
                        "type": "Link",
                        "link_to": CRM_WORKSPACE,
                        "child": 0,
                        "collapsible": 1,
                        "indent": 0,
                        "keep_closed": 0,
                        "show_arrow": 0,
                        "open_in_new_tab": 0,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        done.append("CRM Workspace sidebar")

    if frappe.db.exists("DocType", "Desktop Icon") and not frappe.db.exists("Desktop Icon", CRM_WORKSPACE):
        frappe.get_doc(
            {
                "doctype": "Desktop Icon",
                "label": CRM_WORKSPACE,
                "icon_type": "Link",
                "link_type": "Workspace Sidebar",
                "link_to": CRM_WORKSPACE,
                "icon": "crm",
                "bg_color": "gray",
                "hidden": 0,
                "standard": 0,
            }
        ).insert(ignore_permissions=True)
        done.append("CRM Workspace desktop icon")

    return done


def add_sales_dashboard_to_selling():
    """Put the Sales Dashboard block at the top of the Selling workspace (once)."""
    if not frappe.db.exists("Workspace", "Selling"):
        return False

    workspace = frappe.get_doc("Workspace", "Selling")
    content = json.loads(workspace.content or "[]")

    already_there = any(
        block.get("type") == "custom_block" and block.get("data", {}).get("custom_block_name") == SALES_BLOCK
        for block in content
    )
    if already_there:
        return False

    content = [
        {"id": "sdSalesDashboard", "type": "custom_block", "data": {"custom_block_name": SALES_BLOCK, "col": 12}},
        {"id": "sdSpacer", "type": "spacer", "data": {"col": 12}},
    ] + content
    workspace.content = json.dumps(content)

    if not any(row.custom_block_name == SALES_BLOCK for row in workspace.get("custom_blocks") or []):
        workspace.append("custom_blocks", {"custom_block_name": SALES_BLOCK, "label": SALES_BLOCK})

    workspace.flags.ignore_permissions = True
    workspace.save()
    return True


def install_dashboards():
    """Create everything. Each step is independent, so one failure never blocks the rest.

    Returns a list of what was created.
    """
    done = []

    steps = (
        ("blocks", create_blocks),
        ("CRM workspace", create_crm_workspace),
        ("Selling workspace", add_sales_dashboard_to_selling),
    )
    for label, step in steps:
        try:
            result = step()
        except Exception:
            frappe.log_error(title=f"RIC dashboards: {label} failed")
            continue

        if isinstance(result, list):
            done.extend(result)
        elif result:
            done.append("Sales Dashboard added to Selling workspace")

    return done
