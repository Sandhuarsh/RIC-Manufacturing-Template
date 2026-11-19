# RIC Template

Rapid Implementation Cockpit (RIC) template app for ERPNext / Frappe. It holds the reusable
MSME onboarding logic so every new implementation starts from the same configurable base
instead of per-client scripts.

## What is in version 0.0.1: configurable Item codes

Item codes are built from **rules**, one per Item Group, instead of hardcoded scripts.

```
<prefix>[<sub-group abbreviation>-]<running number>
IM-FG-HYD-100001      prefix IM-FG-, sub-group HYD, number 100001
IM-RIM-300001         prefix IM-RIM-, no sub-group abbreviation
```

| Setting (RIC Naming Rule) | Meaning |
|---|---|
| Item Group | The group the rule covers. It also covers every group below it; the nearest rule wins. |
| Prefix | Text at the start of every code. |
| Include Sub-Group Abbreviation | Adds the **RIC Abbreviation** of the item's own group (field added to Item Group). |
| Start / End Number | The number range. Saving fails with a clear message when the range is used up. |
| Number Padding | Minimum digits (6 turns 42 into 000042). 0 keeps the number as is. |
| Last Number Used | Counter, kept up to date automatically. |

Behaviour:

* A new Item saved **with no item code** gets one from its group's rule. The form shows the
  next code while you pick the group.
* An item that already has a code (typed by hand, or imported) is left alone, and so is an item
  whose group has no rule. Standard ERPNext naming applies.
* The counter row is locked while a number is reserved, so two users saving at once never
  receive the same code. Codes that already exist are skipped.

Optional guards (RIC Template Settings, both ON by default):

* **Block Duplicate Item Names**
* **Lock Item Group After Creation**: only for items whose group has a rule.

### Quick start

1. Install the app (below). `RIC Abbreviation` appears on Item Group.
2. In **Stock Settings** set **Item Naming By = Item Code**. With "Naming Series", ERPNext
   replaces the generated code with its own series number.
3. Open **RIC Template Settings** and click **Create Default Item Rules**. This creates the
   manufacturing groups and rules from the RIC Master Data sheet:

   | Group | Prefix | Range |
   |---|---|---|
   | Finished Product | IM-FG- | 100000 - 199999 |
   | Sub Assembly | IM-SF- | 200000 - 299999 |
   | Raw Material | IM-RIM- | 300000 - 399999 |
   | Packing Material | IM-PIM- | 400000 - 499999 |
   | Consumables | IM-CO- | 500000 - 599999 |
   | Services | IM-SR- | 600000 - 699999 |

4. Create the sub-groups under each of these and fill in their **RIC Abbreviation**.
5. Create an Item with only name and group. Leave Item Code empty.

Different client? Edit or add rules in **RIC Naming Rule**. No code changes are needed.

## Credit and debit note numbering

Button **Create Credit/Debit Note Rules** in RIC Template Settings creates standard Frappe
Document Naming Rules (no custom code). Counters are not set, so every series starts at 1.

| Document | Condition | Series |
|---|---|---|
| Sales Invoice | is_return | `CDNR-.YY.-` (sales credit note) |
| Sales Invoice | is_debit_note | `DBNS-.YY.-` (sales debit note) |
| Purchase Invoice | is_return | `DBNR-.YY.-` (purchase debit note, return to supplier) |
| Purchase Invoice | is_debit_note | `DBNP-.YY.-` (debit note received from supplier) |

Rules whose condition field does not exist are skipped (`is_debit_note` needs India
Compliance). Existing rules with the same prefix are left alone. Note that Frappe's counter
does not reset each year; the year is only part of the prefix.

## Install

Bench:

```bash
bench get-app <repository-url> --branch main
bench --site <site> install-app ric_template
bench --site <site> migrate
```

Frappe Cloud: push this folder to a GitHub repository, add it under **Apps** on the bench
group, deploy, then install the app on the site.

Requires Frappe / ERPNext v15 or v16.

## Status

Written from the Supreme Equipments item-code logic and the RIC Master Data sheet. Not yet
installed or run on a live site, so run the checks below on a development site first.

Run the tests on a development site:

```bash
bench --site <dev-site> run-tests --app ric_template
```

## Roadmap

Supplier and Customer numbering, PO / SO number series by document type, and the print formats
from the MFG Template are planned for later versions.
