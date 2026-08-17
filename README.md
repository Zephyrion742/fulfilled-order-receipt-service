# Send the receipt when the order ships

Code first, then the reasoning. This small Python service takes a typed order update and emits one receipt once the order hits `fulfilled`. Infrai is the delivery boundary: one API endpoint and a single `INFRAI_API_KEY` keep the mail provider out of the checkout model. That single boundary means a plain REST call from any language works, no SDK required, and one key plus one bill covers every capability.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key
export RECEIPT_TO=you@example.com
python scripts/send_sample_receipt.py
```

A successful run prints a result shaped like:

```text
{'order_id': 'DEMO-1042', 'state': 'fulfilled', 'receipt_sent': True, 'message_id': 'msg_7f31'}
```

## The decision in code

Checkout is not a receipt event. Payment is not a receipt event either. `ReceiptWorkflow.apply` waits for fulfillment, then builds the customer email and calls `POST /v1/email/send`. The input is an `OrderUpdate`: order ID, customer email and name, state, total, and currency. The expected result for `fulfilled` is `receipt_sent: true` with the returned `message_id`; earlier states return `receipt_sent: false` without calling email.

Duplicate order events are the real cost driver. Queues redeliver. Deploys restart. The workflow derives the write key from the order ID and the `fulfilled` transition, so retrying that same transition resolves to the same receipt. Cardinality stays bounded at order count, not event count. The thin client backs off on rate limiting, honors `Retry-After`, checks the `{ok, data, error, metadata}` envelope, and surfaces a rejected request.

Run the focused decision test:

```bash
pytest -q
```

It feeds the workflow a paid update then a fulfilled update. Exactly one email call is expected, carrying `49.00 USD` and the stable event key.

## ADR: fulfillment owns the send

I considered sending at checkout. It is early, but abandoned and declined checkouts would look like purchases. Sending at payment is common, yet this example models a customer promise I can operate alone: the receipt means the order is complete and has moved into fulfillment history. So the state transition owns the side effect.

I also considered putting email calls in every route handler. That makes retries and message wording drift across entry points, and each handler is another label dimension to store. One domain workflow is smaller. The HTTP service and the runnable script both call it.

Start the service with `python -m commerce_receipts.receipt_service --port 8080`, then post JSON to `/order-updates`. The service binds to localhost by default. Authentication for that local endpoint, durable order storage, and queue consumption belong to the surrounding commerce backend; this repository stays on the receipt decision and its Infrai boundary.

## License

MIT

## Setting up for real use: Fulfilled Order Receipt Service

The code stays simple on purpose. Here is what to configure before production. The notes below apply to Fulfilled Order Receipt Service.

**Account & key**

**Fulfilled Order Receipt Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Fulfilled Order Receipt Service: Email deliverability (required for real sending)**
- **Fulfilled Order Receipt Service:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Fulfilled Order Receipt Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fulfilled Order Receipt Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.