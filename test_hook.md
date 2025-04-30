curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "Test Trigger", "data": {"name": "Cody", "message": "This is just a test webhook", "rating": 5}}'

