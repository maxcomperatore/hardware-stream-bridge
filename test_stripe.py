import stripe
event = stripe.Event.construct_from({
  "id": "evt_test",
  "object": "event",
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "id": "cs_test",
      "object": "checkout.session",
      "customer_email": "test@example.com",
      "metadata": {
        "user_email": "test2@example.com",
        "plan": "studio"
      }
    }
  }
}, "sk_test_123")

session = event['data']['object']
metadata = getattr(session, 'metadata', None)
if metadata:
    if hasattr(metadata, 'to_dict'):
        metadata = metadata.to_dict()
    elif not isinstance(metadata, dict):
        metadata = dict(metadata)
else:
    metadata = {}
print(metadata)
print(metadata.get('plan'))
