# Apps

One Django app per business domain. Key model classes are listed so you can jump to
the right app without grepping the whole repo.

## People & recruitment

| App | Purpose | Key models |
|---|---|---|
| `staff` | HR: employees, payroll, HR actions (permits, suspensions, terminations, welfare) | `Employee`, `Position`, `Payroll`, `Permit`, `Suspend`, `Terminate`, `Welfare`, `StaffStatement` |
| `apply` | Job applications — **current/legacy** applicant data and workflow | `Applicant`, `Interview`, `ApplicationInvite`, `GuarantorDocument` |
| `jobs` | Job postings and applications — the **newer**, more advanced recruitment flow | `JobPosting`, `JobApplication`, `Guarantor` |
| `users` | Auth-adjacent: user profiles and the invite-based registration system | `Profile`, `UserInvite` |

`apply` and `jobs` are **not** duplicates — `apply` holds the existing/legacy
applicant pipeline, `jobs` is the newer recruitment system being built out. Check
which one a task actually refers to before assuming they should be merged.

## Stock & warehousing

| App | Purpose | Key models |
|---|---|---|
| `stock` | Inventory: products, stock movements, stock counts, pricing history | `Product`, `Category`, `StockMovement`, `StockCountSession`, `PriceHistory` |
| `warehouse` | Physical stores/warehouses, levies, renewals | `Stores`, `StoreLevy`, `Renewal`, `BankAccount` |
| `material` | Internal material/article requests and issuance | `Article`, `RequestArticle`, `IssueArticle` |
| `delivery` | Scoped for **outbound deliveries to customers only** — not goods receipt (that's `stock`'s Goods Received flow). Scaffolded (migrations only) but not yet registered in `INSTALLED_APPS` / `ozone/urls.py`. | — |

## Finance & trade

| App | Purpose | Key models |
|---|---|---|
| `trade` | Trade/financial reporting: daily & monthly trade, balance sheets, budgets, audit log | `TradeMonthly`, `TradeDaily`, `BalanceSheet`, `TradeBudget`, `TradeAuditLog` |
| `cashflow` | Cash and bank transaction tracking: deposits, disbursements, transfers | `BankAccount`, `CashTransaction`, `Disburse`, `InterbankTransfer` |
| `target` | Sales/KPI targets and budgets | `BudgetYear`, `SalesTarget`, `KPIBudget`, `KPIMonthlyTarget` |
| `outlet` | Sales centers | `SalesCenter` |

## Customers & comms

| App | Purpose | Key models |
|---|---|---|
| `customer` | Customer records and credit | `Profile`, `CustomerCredit` |
| `comms` | Internal comms — posts, projects/tasks, polls. Replaced the older `pdf_convert`, `mails`, `brief`, and `survey` apps, which were retired. | `Post`, `Project`, `Task`, `Poll` |

## Cross-cutting / legacy utility apps

| App | Purpose |
|---|---|
| `core` | Shared settings (`Setting`, `CompanyProfile`), JSON datasets, mounted at `/`, hosts this docs site |
| `pdf` | PDF generation utilities (no models, not URL-namespaced under its own prefix pattern like newer apps) |
| `mail` | Mail templates/mailbox helpers (no models) |

## Finding a URL prefix

App directory names don't always match their URL prefix — see
[`ozone/urls.py`](../architecture/overview.md#url-routing-ozoneurlspy) for the actual
mapping (e.g. `stock` is mounted at `/product/`, `warehouse` at `/store/`).
