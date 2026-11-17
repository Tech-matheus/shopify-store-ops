# Shopify Bulk Product Importer

A Python tool that syncs a product spreadsheet (CSV) with a Shopify store through the Admin GraphQL API.

It validates every row before touching the store, plans what has to be created or updated, and by default only simulates. It writes to the store only when you ask for it.

## What it does

- **Validates the spreadsheet** and reports each problem by line number: invalid or repeated SKU, missing title, invalid price, invalid stock, image link that is not HTTPS.
- **Plans before acting.** For each valid row it checks the store by SKU and decides: create, update, keep (already equal) or skip.
- **Updates only what changed** (title, product type, price, stock), and shows the before and after.
- **Dry run by default.** Nothing is sent to the store unless you pass `--aplicar`.
- **Protects the store.** Products with several variants are skipped, and stock is only written if it was not changed by someone else in the meantime.
- **Writes a report** to `relatorios/resultado_importacao.csv`.

New products are created as **drafts**, so the store owner can review them before publishing.

## How it works

```
CSV  ->  validate rows  ->  look up each SKU in the store  ->  plan  ->  execute (or simulate)  ->  report
```

| Situation in the store | Action |
| --- | --- |
| SKU does not exist | create (draft) |
| SKU exists and something changed | update only the changed fields |
| SKU exists and everything is equal | keep |
| SKU repeated in the store, several variants, or not stocked at the chosen location | skip |

## Requirements

- Python 3.14 (the version it was developed and tested on; older versions were not tested)
- A Shopify store (a free development store from Shopify Partners works)
- An app created in the Shopify Dev Dashboard, installed on the store, with these access scopes:
  `read_products, write_products, read_orders, read_inventory, write_inventory, read_locations`

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (it is ignored by Git):

```
SHOPIFY_SHOP=your-store-subdomain
SHOPIFY_CLIENT_ID=...
SHOPIFY_CLIENT_SECRET=...
SHOPIFY_LOCAL_ESTOQUE=Shop location
```

`SHOPIFY_SHOP` is the part before `.myshopify.com`. The tool asks Shopify for a short-lived access token (24 hours) with the client credentials grant, so no token is stored. The app and the store must belong to the same Shopify organization.

## Spreadsheet format

Separator `;` or `,`. Decimal prices like `59,90`, `59.90` and `1.299,90` are accepted.

```
sku;titulo;preco;estoque;tipo;imagem_url
CAM-001;Camiseta Básica Preta;59,90;25;Camisetas;
```

`sku`, `titulo`, `preco` and `estoque` are required. A sample file is in `dados/produtos_exemplo.csv`, with intentional errors.

## Usage

```
python validar_planilha.py          # only validates the spreadsheet
python importar.py                  # dry run: shows the plan, changes nothing
python importar.py --aplicar        # applies the plan to the store
python importar.py other_file.csv   # use another spreadsheet
```

## Tests

```
python -m pytest -q
```

35 tests cover the validation rules, the planning decisions and the execution step. The Shopify API is replaced by a fake client in the tests, so they run offline.

## Security notes

- Credentials live only in `.env`, never in the code or the repository.
- The importer does not read customer data.
- Everything was tested on a Shopify development store with sample data.

## Limitations

- Only simple products (one variant). Products with several variants are skipped on purpose.
- Product images in the spreadsheet are validated but not imported yet.
- No automatic retry when Shopify rate limits requests. This is fine for small spreadsheets, but would be needed for large catalogs.
- User-facing messages are in Portuguese.

## Store Ops API (FastAPI)

A small read-only API on top of the same Shopify store. It answers the questions a store owner asks every day, and exports an Excel report.

| Endpoint | What it does |
| --- | --- |
| `GET /saude` | Health check |
| `GET /produtos?limite=20` | Product list: SKU, title, status, price, stock |
| `GET /estoque/baixo?ate=5` | Active, stock-tracked products at or below a stock level |
| `GET /pedidos/resumo?dias=30` | Orders, revenue, average ticket, items sold and top 5 products for the last N days (max 60) |
| `GET /relatorio.xlsx?dias=30&ate=5` | Excel report with 3 sheets: Summary, Top products, Low stock |

### Run it

```
pip install -r requirements.txt
uvicorn store_ops.api.app:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the interactive documentation.

### Design notes

- Read-only: the API never changes the store.
- Cancelled orders are counted separately and excluded from revenue.
- No customer personal data is read or stored: only totals, quantities and product names. The app only needs protected customer data access level 1.
- Pagination with cursors, so stores with more than 100 products are handled (up to 1000 variants).
- If Shopify fails, the API answers `502` without leaking internal details.
- The Shopify client is injected, so tests run with fake clients and never touch the real store.

### Limitations

- Orders are limited to the last 60 days (the default window for the `read_orders` scope).
- Product list and low stock look at up to 1000 variants.
- Gift cards and other items without stock tracking are not listed as low stock.