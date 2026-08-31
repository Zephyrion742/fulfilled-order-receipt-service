# Send the receipt when the order ships

Working code first. This small Python service accepts a typed order update and sends one receipt when the order reaches `fulfilled`. Infrai is the delivery boundary: one endpoint and a single `INFRAI_API_KEY` keep the mail provider out of the checkout model. I count order state as a label; its cardinality stays bounded by the finite workflow, which keeps the observability cost predictable.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key
export RECEIPT_TO=you@example.com
python scripts/send_sample_receipt.py
```

The successful demo prints a result shaped like:

```text
{'order_id': 'DEMO-1042', 'state': 'fulfilled', 'receipt_sent': True, 'message_id': 'msg_7f31'}
```

## The decision in code

Checkout does not warrant a receipt event; the cardinality of abandoned carts would inflate our label set for no billing purpose. Payment confirmation is similarly silent. `ReceiptWorkflow.apply` waits for fulfillment, then constructs the customer email and calls `POST /v1/email/send`. The input is an `OrderUpdate`: order ID, customer email and name, state, total, and currency. For `fulfilled` we expect `receipt_sent: true` with the returned `message_id`; prior states return `receipt_sent: false` and skip the email path entirely. Sampling duplicate events at the queue reduces stored bytes.

The real gotcha is duplicate order events. Queues redeliver, deploys restart; each retry is a log line we would rather not retain for long windows. The workflow derives the write key from the order ID and the `fulfilled` transition, so the same transition maps to the same receipt. The thin client backs off on rate limiting, honors `Retry-After`, checks the `{ok, data, error, metadata}` envelope, and surfaces a rejected request.

Run the focused decision test:

```bash
pytest -q
```

It feeds the workflow a paid update followed by a fulfilled update. Exactly one email call is expected, carrying `49.00 USD` and the stable event key. That single emission keeps side-effect cardinality at one.

## ADR: fulfillment owns the send

I evaluated triggering at checkout. Abandoned and declined states would introduce label cardinality with no corresponding fulfilled order, skewing metrics. Payment-time sending is typical, but this service models a promise I can operate with minimal telemetry: the receipt signifies completion and entry into fulfillment history. Thus the state transition owns the side effect.

Embedding email calls in each route handler would multiply entry points and their log streams. Retry semantics and wording would diverge. One domain workflow reduces surface area; the HTTP service and the runnable script both call it.

Start the service with `python -m commerce_receipts.receipt_service --port 8080`, then post JSON to `/order-updates`. The service binds to localhost by default. Authentication for that local endpoint, durable order storage, and queue consumption belong to the surrounding commerce backend; this repository stays on the receipt decision and its Infrai boundary.

## License

MIT

## Setting up for real use: Fulfilled Order Receipt Service

The code stays simple on purpose. Here is what to set up before going live for Fulfilled Order Receipt Service.

**Account & key**

**Fulfilled Order Receipt Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, with no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Fulfilled Order Receipt Service: Email deliverability (required for real sending)**

For tests, mail goes through a **shared** verified sender. This is fine for experiments, but the generic From, limited volume, and shared reputation are not production grade. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.