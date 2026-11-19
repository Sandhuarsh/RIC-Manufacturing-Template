app_name = "ric_template"
app_title = "RIC Template"
app_publisher = "Innosphere Consulting"
app_description = "Rapid Implementation Cockpit (RIC) template: configurable master data numbering for MSME ERPNext implementations"
app_email = ""
app_license = "mit"

# Installation
# ------------
after_install = "ric_template.install.after_install"
after_migrate = "ric_template.install.ensure_custom_fields"

# Client side
# -----------
doctype_js = {"Item": "public/js/item.js"}

# Document events
# ---------------
doc_events = {
    "Item": {
        "before_insert": "ric_template.naming.set_item_code",
        "validate": "ric_template.naming.validate_item",
    }
}
