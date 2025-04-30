curl -X POST http://192.168.1.66:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "Test Trigger", "data": {"name": "Cody", "message": "This is just a test webhook", "rating": 5}}'

curl -X POST http://192.168.1.66:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "Celebration", "data": {"name": "Cody Viveiros", "message": "Cody just finished all the IT tasks in his task his, give him a round of applause", "rating": 5}}'

curl -X POST http://192.168.1.66:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "Cody Viveiros", "message": "Cody is the coolest of them all"}}'

curl -X POST https://4ad8-68-71-74-65.ngrok-free.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "Cody Viveiros", "message": "Cody is the coolest of them all"}}'

curl -X POST https://4ad8-68-71-74-65.ngrok-free.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "success", "data": {"name": "Wilbur", "message": "wilbur made a happy plate", "rating": 5}}'

Per Christian, he said ok to get Chris Harrison a new cp.  His took a tumble, Christian said you might even have an extra there already, if not he said ok to get one.  Again this is for Chris Harrison, my co-worker.

  https://4ad8-68-71-74-65.ngrok-free.app


curl -X POST https://4ad8-68-71-74-65.ngrok-free.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"data": {"Name": "Cody Viveiros", "message": "Cody has fixed all the problems, all it tickets are complete"}}'



  {
  "Name": "{{ body | regex_extract: 'Name:\\s*(.*)' }}",
  "Department": "{{ body | regex_extract: 'Department:\\s*(.*)' }}",
  "Location": "{{ body | regex_extract: 'Location:\\s*(.*)' }}",
  "Issue Description": "{{ body | regex_extract: 'Issue Description:\\s*([\\s\\S]*?)Attachments:' }}"

INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:root:GPT Summary: Tech Master, the shrouded enigma known as ${extracted_name}, from the abyss of ${extracted_dept} in ${extracted_loc}, beckons your aid with a cryptic quandary - ${extracted_issue}.
ffplay version 7.1-full_build-www.gyan.dev Copyright (c) 2003-2024 the FFmpeg developers
  built with gcc 14.2.0 (Rev1, Built by MSYS2 project)
