"""Phase 7: Validate evidence IDs in output.csv against message_history.csv."""
import csv

history_ids = set(r['message_id'] for r in csv.DictReader(open('dataset/message_history.csv', encoding='utf-8')))
print(f"Historical message IDs: {len(history_ids)}")

rows = list(csv.DictReader(open('outputs/output.csv', encoding='utf-8')))
invalid_count = 0
total_ev = 0
invalid_examples = []

for row in rows:
    ev_str = row['evidence_message_ids']
    if ev_str != 'none':
        ev_ids = [e.strip() for e in ev_str.split(';')]
        for ev_id in ev_ids:
            total_ev += 1
            if ev_id not in history_ids:
                invalid_count += 1
                if len(invalid_examples) < 5:
                    invalid_examples.append((row['message_id'], ev_id))

print(f"Total evidence IDs checked: {total_ev}")
print(f"Invalid (not in message_history): {invalid_count}")
print(f"Valid: {total_ev - invalid_count}")
if invalid_examples:
    print("Examples of invalid evidence:")
    for row_id, ev_id in invalid_examples:
        print(f"  Row: {row_id} -> Bad evidence: {ev_id}")
