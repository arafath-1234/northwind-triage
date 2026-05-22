Write-up — Northwind Triage Agent

Accuracy Scores
FieldScoreStrict accuracy (all 4 fields)17/20 = 85.0%
Category19/20 = 95.0%
Priority18/20 = 90.0%
Route to20/20 = 100.0%
Needs human review19/20 = 95.0%

85% strict accuracy means all 4 fields matched on 17 out of 20 messages. The 3 misses are not random — I can explain every one of them, and in two cases I think the benchmark is wrong, not my agent.

Agent Design
Single prompt, single Claude call per message. No chaining, no multi-agent routing, no orchestration layer. The system prompt encodes the full SOP, service catalogue, and tone guide as structured plain text. Claude reasons over it and returns JSON.
I kept it simple on purpose. This is a bounded classification problem — fixed rules, fixed categories, fixed output schema. Every layer of complexity I add is another thing that can break. A well-written prompt on a capable model handles this cleanly. I didn't want to build five agents and a router for a problem that fits in one prompt.
For the model I went with claude-sonnet-4-5. The task has layered conditional logic season, service type, time of day, dollar amounts all interact. Haiku handles simple classification well but gets inconsistent when multiple rules fire at once. Opus would probably score higher but it's slower and more expensive than this task warrants. Sonnet sits in the right spot — strong enough to follow complex rules reliably, fast enough for a live UI.

Benchmark Disagreements
1. MSG-007 — Rachel Ford (broken dishwasher)
Benchmark says: needs_human_review: true
My agent said: needs_human_review: false
I disagree with the benchmark here.
I went back to the catalogue. Under "Things we do not do" it explicitly lists: "Appliance repair (washing machines, dishwashers, ovens) we install but do not repair." That is not a grey area. That is a named, specific exclusion.
The point of human review is to catch things the agent cannot confidently decide. But here there is nothing to decide the answer is always the same. A human reviewer looking at this message would decline it in five seconds and move on. Flagging it wastes their time and, more importantly, buries real escalations under unnecessary noise. Unnecessary flags are not "safe" — they make the review queue meaningless. My agent got this right.

2. MSG-009 — Linda M. (ducted heater stopped working, winter evening)
Benchmark says: BOOKING, P2
My agent said: EMERGENCY, P1
The benchmark is right. My agent got this wrong.
I understand why the agent went EMERGENCY a heater breaking on a cold winter night does feel urgent. But there is a difference between something feeling urgent and something being a P1 emergency. The SOP's P1 definition is about active risk to safety or property. Something has to be getting worse right now water flowing through a ceiling, electricity sparking, gas leaking. A broken heater is uncomfortable, maybe seriously so, but nothing is escalating. No damage is happening. The person can get through the night.
There is also a practical reason this cannot be P1: Northwind has no on-call HVAC team. If the agent classifies this as P1, the draft reply promises same-day service that simply does not exist. That is worse than being upfront you've raised the customer's expectations and then cannot meet them.
This is a prompt failure on my side. The no on-call HVAC rule is in the system prompt, but the model still overrode it because the message felt like an emergency. The fix is adding an explicit example: "broken heater in winter = P2 BOOKING, not EMERGENCY, because HVAC has no on-call." Models follow concrete examples better than abstract rules alone.

3. MSG-019 — Catherine Lowe ($720 refund, 14 days overdue)
Benchmark says: P2
My agent said: P3
The benchmark is right, but the SOP doesn't actually get you there.
The strict SOP rule for P2 is: loss of essential function, or a complaint over $1,000. This is neither — it's a $720 refund on a cancelled job, and the amount is under $1,000. So technically my agent's P3 is correct by the letter of the SOP.
But that misses what is actually happening. Catherine was explicitly promised a refund within 10 business days. It has been 14 days. She is not raising a new query she is chasing something Northwind already committed to. That changes the nature of the message entirely. Treating a broken promise the same as a new billing enquiry is wrong, even if the SOP doesn't have a specific rule for it.
Beyond the money, there is a reputational risk. A customer waiting on a confirmed refund with no communication is exactly the kind of person who leaves a public review. The cost of treating this as P2 is low. The cost of getting it wrong is not.

4. MSG-004 — Daniel O'Brien (billing dispute, $150 overcharge)
My agent matched the benchmark — Customer Care + Accounts, P2, needs_human_review: true.
But I want to flag something.
The SOP says: "if a COMPLAINT involves a billing dispute over $500, cc Accounts." The disputed amount here is $150. The total invoice is $720, but that is the job cost not the dispute. The dispute is $150, well under the threshold. Strictly by the SOP, this should route to Customer Care only.
The benchmark cc's Accounts anyway, and I think that judgment call is right someone needs to confirm whether the upper-floor surcharge was actually disclosed during the quote. But the benchmark is overriding its own $500 rule without acknowledging it. That matters in a production system. When you quietly break your own rules, even for good reasons, the rules stop meaning anything over time.

Where the Agent Can Fail
Customers exaggerating to get faster service
The agent classifies on what the customer writes. If someone describes a minor drip as "water coming through the ceiling" to get a P1 response, the agent will classify it as EMERGENCY — it has no way to verify. I thought about this, but it is not really an agent problem. It is a commercial problem, and the catalogue already handles it: after-hours call-outs carry surcharge rates. A customer who exaggerates to get same-day service pays after-hours pricing for it. That is the deterrent. The tradesperson who shows up makes the real assessment. The agent's job is classification, not verification.

Non-English messages
MSG-018 came in as Spanish. The agent correctly identified it as a P1 EMERGENCY  water coming from the hot water system, customer in Parramatta, clearly urgent. It responded in English, which is correct given Northwind does not promise multilingual support. But this only worked because the model understands Spanish well. A message in a less common language could be misread as garbled and classified OUT_OF_SCOPE which means a real emergency gets missed. The SOP says flag non-English for human review, and the agent does that. But before using this in production I would test it with a wider range of languages to understand where that safety net actually holds.

Tone
The hard rules hold across all 20 messages no exclamation marks, no emoji, no "from" prices quoted, no tradesperson names, no "thank you for contacting Northwind." Every draft reply opens with the customer's specific situation, not a generic opener.
One small thing I noticed: a few replies say "will call you today" instead of "within the day." They mean the same thing but "within the day" matches SOP language more precisely and avoids any reading of an exact time commitment. Small thing, worth tightening.

What I'd Build Next:

The tool currently shows the triage decision. The dispatcher still has to act on it manually copy the draft, figure out who to notify, send it themselves. The obvious next step is closing that gap: auto-routing.
The routing keys are already there. route_to tells you which team. needs_human_review tells you whether a human needs to see it. You just need to connect those to a destination a Gmail forward, a Slack webhook, a ticket in whatever system Northwind uses. The implementation depends on their stack, but the data model is already right.
The part that needs thought is time-awareness. A P1 EMERGENCY at 11pm should fire immediately SMS the on-call dispatcher, no delay. But a P2 at 11pm should not alert anyone overnight. The SOP is explicit: after hours, only P1 is actioned live. Everything else queues for the next business morning. The received_at timestamp is already on every message, so a business hours check before routing is straightforward. Without it you are waking people up for jobs that were never going to happen until tomorrow anyway.
That is the one thing that would turn this from a classification display into something a dispatcher actually relies on every day.

One Place the Documents Contradict Each Other

The catalogue says EV charger installation requires a minimum property service age of 12 months. The SOP says if unsure between QUOTE and BOOKING, default to QUOTE and let Sales confirm scope. The tone guide says be honest, not performative.
These pull in different directions. If a customer from a brand new development asks for an EV charger quote, the SOP says send it to Sales as a QUOTE. But the honest thing — which the tone guide pushes for is to flag the eligibility question upfront rather than let the customer wait for a quote that might come back as "sorry, not yet."
My resolution: classify as QUOTE, route to Sales, and add a line in the draft reply that the team will confirm eligibility when they follow up. The SOP routing is respected, the customer is not misled, and Sales has the context they need. It is a small thing but it is the kind of tension that causes customer complaints if nobody catches it at triage.