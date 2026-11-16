"""Generate the fixed, source-cited 20-scenario evaluation corpus."""
import json
from pathlib import Path
PASSAGES={
"cancel_331":{"citation":"DGCA_Passenger_Rights.pdf, page 5, paragraph 3.3.1","text":"The airline shall inform the passenger of cancellation at least two weeks before scheduled departure and arrange alternate flight/refund as acceptable. When informed less than two weeks and up to 24 hours before departure, offer alternate flight or refund as acceptable."},
"cancel_332":{"citation":"DGCA_Passenger_Rights.pdf, page 5, paragraph 3.3.2","text":"Passengers not informed as required by 3.3.1, or who missed a same-ticket connection, shall receive either an acceptable alternate flight or compensation in addition to a full ticket refund. Facilities under 3.8.1(a) apply while waiting for the alternate flight."},
"cancel_333":{"citation":"DGCA_Passenger_Rights.pdf, page 5, paragraph 3.3.3","text":"No financial compensation is payable to passengers who did not provide adequate contact information at booking. The airline shall refund the ticket or make reasonable alternate travel arrangements; facilities apply while waiting for an alternate flight."},
"cancel_334":{"citation":"DGCA_Passenger_Rights.pdf, page 6, paragraph 3.3.4","text":"No compensation is payable for cancellations caused by extraordinary circumstances beyond airline control as described in paragraphs 1.4 and 1.5."},
"delay_341a":{"citation":"DGCA_Passenger_Rights.pdf, page 6, paragraph 3.4.1(a)","text":"Facilities under paragraph 3.8.1(a) apply for a checked-in passenger if delay is 2 hours or more for flights with block time up to 2.5 hours."},
"delay_341b":{"citation":"DGCA_Passenger_Rights.pdf, page 6, paragraph 3.4.1(b)","text":"Facilities apply for a checked-in passenger if delay is 3 hours or more for flights with block time more than 2.5 and up to 5 hours."},
"delay_341c":{"citation":"DGCA_Passenger_Rights.pdf, page 6, paragraph 3.4.1(c)","text":"Facilities apply when expected delay is 4 hours or more for flights not falling under the preceding block-time bands."},
"delay_342":{"citation":"DGCA_Passenger_Rights.pdf, page 6, paragraph 3.4.2","text":"When a domestic flight is expected to be delayed more than 6 hours, the airline shall offer an alternate flight within 6 hours or a full refund."},
"delay_343":{"citation":"DGCA_Passenger_Rights.pdf, pages 6-7, paragraphs 3.4.3 and 3.8.1(b)","text":"When total delay is more than 24 hours, or more than 6 hours for flights scheduled 2000-0300, facilities under 3.8.1(b) apply. These include hotel accommodation when necessary, including transfers."},
"delay_344":{"citation":"DGCA_Passenger_Rights.pdf, page 6, paragraph 3.4.4","text":"The airline is not obliged to provide paragraph 3.8 facilities when delay is caused by extraordinary circumstances under paragraphs 1.4 and 1.5 that could not have been avoided despite reasonable measures."},
"downgrade_dom":{"citation":"DGCA_Passenger_Rights.pdf, page 6, paragraph 3.5.1(a)","text":"For a domestic sector, involuntary downgrading requires reimbursement of 75% of ticket cost including taxes."},
"downgrade_intl":{"citation":"DGCA_Passenger_Rights.pdf, page 7, paragraph 3.5.1(b)","text":"For international sectors, reimbursement including taxes is 30% for 1500 km or less, 50% between 1500 km and 3500 km, and 75% above 3500 km."},
"facilities":{"citation":"DGCA_Passenger_Rights.pdf, page 7, paragraph 3.8.1","text":"Passengers shall be offered free of charge meals and refreshments in relation to waiting time. Hotel accommodation including transfers is provided when necessary."}}
CASES=[
("S01-section-4-1","My flight was cancelled. I was at the airport and told 90 minutes before departure. The airline put me on a flight four hours later, which I took. I want cancellation compensation.","decline","cancel_332",["alternate flight","compensation","full ticket refund","facilities"]),
("S02-cancellation-14-days","Cancellation notice arrived 16 days before departure and an alternate flight was offered.","request_further_evidence","cancel_331",["two weeks","alternate flight","refund"]),
("S03-cancellation-48-hours","Cancellation was communicated 48 hours before departure; what are my options?","request_further_evidence","cancel_331",["24 hours","alternate flight","refund"]),
("S04-cancellation-12h-no-alternate","I was told my flight was cancelled 12 hours before departure and no alternate or refund was offered.","request_further_evidence","cancel_332",["alternate flight","compensation","full ticket refund"]),
("S05-cancellation-alternate-taken","Cancellation notice was 12 hours before departure; I accepted and took an alternate flight.","decline","cancel_332",["either","alternate flight","compensation"]),
("S06-cancellation-no-contact","My booking had no phone or email contact information; the cancelled flight was replaced.","decline","cancel_333",["no financial compensation","contact information","facilities"]),
("S07-cancellation-force-majeure","The airline says cancellation was caused by extraordinary circumstances; the cause is disputed.","escalate_to_human","cancel_334",["extraordinary circumstances","beyond airline control"]),
("S08-waiting-meals","I waited at the airport for an alternate flight after cancellation. Were meals and refreshments due?","pay_as_computed","facilities",["free of charge","meals","refreshments"]),
("S09-same-ticket-connection","I missed a connecting flight booked on the same ticket number after a disruption.","request_further_evidence","cancel_332",["same-ticket connection","alternate flight","full ticket refund"]),
("S10-delay-short-block","Checked in on time; expected delay is 2 hours, block time is 2 hours.","pay_as_computed","delay_341a",["checked-in","2 hours or more","facilities"]),
("S11-delay-medium-block","Checked in; 4-hour block-time flight is expected to be delayed 3 hours.","pay_as_computed","delay_341b",["3 hours or more","block time","facilities"]),
("S12-delay-long-block","Checked in for a 6-hour block-time flight; expected delay is 4 hours.","pay_as_computed","delay_341c",["4 hours or more","facilities"]),
("S13-domestic-delay-over-six","Domestic flight departure is expected to be delayed more than 6 hours.","request_further_evidence","delay_342",["domestic","more than 6 hours","alternate flight","full refund"]),
("S14-delay-over-24-hours","Total flight delay is 25 hours; I need hotel accommodation.","request_further_evidence","delay_343",["more than 24 hours","hotel accommodation","transfers"]),
("S15-night-delay","A flight scheduled for 23:00 was delayed 7 hours.","request_further_evidence","delay_343",["2000-0300","more than 6 hours","hotel"]),
("S16-delay-cause-disputed","The airline says delay was caused by extraordinary circumstances; cause is contested.","escalate_to_human","delay_344",["extraordinary circumstances","reasonable measures"]),
("S17-domestic-downgrade","I was involuntarily carried in a lower class on a domestic sector.","pay_as_computed","downgrade_dom",["involuntary","domestic","75%","including taxes"]),
("S18-international-downgrade-1200","I was involuntarily downgraded on an international flight of 1200 km.","pay_as_computed","downgrade_intl",["international","1500 km or less","30%"]),
("S19-international-downgrade-2600","I was involuntarily downgraded on an international flight of 2600 km.","pay_as_computed","downgrade_intl",["1500 km and 3500 km","50%"]),
("S20-international-downgrade-4000","I was involuntarily downgraded on an international flight of 4000 km.","pay_as_computed","downgrade_intl",["above 3500 km","75%"])]
rows=[]
for id,complaint,outcome,key,terms in CASES:
    rows.append({"id":id,"claim":{"complaint":complaint},"expected_outcome":outcome,"supporting_passage":PASSAGES[key],"required_facts":terms})
Path(__file__).with_name("scenarios.json").write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding="utf-8")
