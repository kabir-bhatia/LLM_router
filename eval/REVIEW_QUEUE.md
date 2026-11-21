**RESOLVED: reviewed 2026-11-20 (by the parent session on Kabir's behalf); decisions are in eval/results/phase1_report.md.**

# Review queue (Phase 1, step 5)

**You must review this before the dataset is frozen.** Nothing in `eval/tasks_8cat.json` exists yet;
step 6 starts only after you answer. For each item tick one decision (or write the change).

How to read it: *Gold* is what the grader will treat as the right answer. *Note* is the one-line
reason. *GLM said* is an independent answer from glm-5.3-flash that never saw the gold.

NER conventions to keep in mind: span = full proper name ("Bank of America" is one ORG); titles
("Dr.") and possessive 's are not part of a span; DATE = explicit dates, month-year or year only.

What the disagreements look like: 2 sentiment items are genuinely ambiguous (neutral vs a reading of
the quoted word as negative/positive); the factual ones are mostly GLM leaving out a key point (or
adding an unlisted figure); the summary ones are almost all GLM leaving out one of the key facts under a
tight word limit. That second kind may mean my key-fact lists are too demanding for the limit: if you
think so, answer 'drop key fact N' on that item rather than changing the passage.

Totals: 56 items = 14 GLM disagreements + 27 sampled agreements (of 136) + 15 hand-written NER items.

## Batch 1 (10 items)

#### sent-010  (sentiment, hard, phrasing: embedded)
Why it is here: GLM disagrees (or no usable answer)

> We're triaging customer feedback. Here is one entry:
> 
> Customer says the product 'broke' - please confirm the serial number before we open a claim.
> 
> Tag its overall sentiment (positive / negative / mixed / neutral) and say why in a sentence.

- **Gold:** **neutral**
- **Note:** Process request; the quoted 'broke' is reported, not an expressed feeling.
- **GLM said:** The message reports a product breaking, which conveys a negative customer experience despite its procedural tone.  ANSWER: negative
- **GLM check:** GLM label=negative, gold=neutral
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### sent-037  (sentiment, easy, phrasing: labelled)
Why it is here: random 20% sample of GLM-agreed items

> Classify the sentiment of this review as positive, negative, mixed or neutral, then give a one-line reason: 'Great location and friendly host, but the room was noisy and small.'

- **Gold:** **mixed**
- **Note:** Positives about location/host, negatives about the room.
- **GLM said:** The review praises the location and host but criticizes the noise and room size, balancing good and bad points.  ANSWER: mixed
- **GLM check:** GLM label=mixed, gold=mixed
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### sent-006  (sentiment, hard, phrasing: question)
Why it is here: random 20% sample of GLM-agreed items

> Is this review positive, negative, mixed or neutral? Explain briefly.
> 
> "Not bad at all - honestly the best ramen I've had outside Japan."

- **Gold:** **positive**
- **Note:** 'Not bad' opens a superlative compliment.
- **GLM said:** The reviewer praises the ramen as the best they've had outside Japan, which is clearly favorable despite the understated opening.  ANSWER: positive
- **GLM check:** GLM label=positive, gold=positive
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### sent-043  (sentiment, easy, phrasing: casual)
Why it is here: random 20% sample of GLM-agreed items

> what's the vibe of this message - positive, negative, mixed, or neutral? "Best customer service I've had in years - they fixed my issue in five minutes!"

- **Gold:** **positive**
- **Note:** Explicit superlative praise of support.
- **GLM said:** The message expresses strong satisfaction and praise for the quick, effective service.  ANSWER: positive
- **GLM check:** GLM label=positive, gold=positive
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### sent-032  (sentiment, hard, phrasing: casual)
Why it is here: random 20% sample of GLM-agreed items

> what's the vibe of this tweet - positive, negative, mixed, or neutral? "Wow, a whole hour to deliver a cold sandwich. Truly a new record."

- **Gold:** **negative**
- **Note:** Sarcasm about slow, poor delivery.
- **GLM said:** The tweet uses sarcasm ("Truly a new record") to complain about slow delivery, expressing frustration rather than genuine praise.  ANSWER: negative
- **GLM check:** GLM label=negative, gold=negative
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### sent-013  (sentiment, hard, phrasing: question)
Why it is here: random 20% sample of GLM-agreed items

> Is this review positive, negative, mixed or neutral? Explain briefly.
> 
> "Decent camera and a gorgeous display; the speaker is tinny and the software is buggy."

- **Gold:** **mixed**
- **Note:** Two clear positives, two clear negatives.
- **GLM said:** The review praises the camera and display but criticizes the speaker and software, containing both positive and negative points.  ANSWER: mixed
- **GLM check:** GLM label=mixed, gold=mixed
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### sent-035  (sentiment, hard, phrasing: casual)
Why it is here: random 20% sample of GLM-agreed items

> what's the vibe of this review - positive, negative, mixed, or neutral? "The cafe was fine. Nothing special, nothing wrong."

- **Gold:** **neutral**
- **Note:** Deliberately flat evaluation.
- **GLM said:** The review expresses neither satisfaction nor dissatisfaction, just an unremarkable, indifferent assessment.  ANSWER: neutral
- **GLM check:** GLM label=neutral, gold=neutral
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### sent-001  (sentiment, easy, phrasing: embedded)
Why it is here: random 20% sample of GLM-agreed items

> We're triaging customer feedback. Here is one entry:
> 
> I'm furious - I've been charged twice and nobody will help me.
> 
> Tag its overall sentiment (positive / negative / mixed / neutral) and say why in a sentence.

- **Gold:** **negative**
- **Note:** Anger about a billing error.
- **GLM said:** The customer expresses anger and frustration over a double charge and lack of support, with no positive elements.  ANSWER: negative
- **GLM check:** GLM label=negative, gold=negative
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### sent-025  (sentiment, hard, phrasing: labelled)
Why it is here: random 20% sample of GLM-agreed items

> Classify the sentiment of this review as positive, negative, mixed or neutral, then give a one-line reason: 'The acting was superb and the cinematography breathtaking, but I walked out feeling I'd wasted three hours on a story that went nowhere.'

- **Gold:** **mixed**
- **Note:** Strong praise and a strong criticism of equal weight.
- **GLM said:** The review praises the acting and cinematography but criticizes the story as pointless, combining strong positives and negatives. ANSWER: mixed
- **GLM check:** GLM label=mixed, gold=mixed
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### sent-026  (sentiment, easy, phrasing: casual)
Why it is here: random 20% sample of GLM-agreed items

> what's the vibe of this review - positive, negative, mixed, or neutral? "Great value for money; these headphones sound far better than I expected."

- **Gold:** **positive**
- **Note:** Exceeded expectations, positive value judgement.
- **GLM said:** The review praises both the price and the sound quality with no complaints, making it clearly favorable.  ANSWER: positive
- **GLM check:** GLM label=positive, gold=positive
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

## Batch 2 (10 items)

#### sent-038  (sentiment, easy, phrasing: embedded)
Why it is here: random 20% sample of GLM-agreed items

> We're triaging customer feedback. Here is one entry:
> 
> Terrible experience. The package arrived two weeks late and the box was crushed.
> 
> Tag its overall sentiment (positive / negative / mixed / neutral) and say why in a sentence.

- **Gold:** **negative**
- **Note:** Lateness and damage, explicit 'terrible'.
- **GLM said:** The customer complains about a late delivery and damaged packaging with no redeeming remarks, making the sentiment clearly negative.  ANSWER: negative
- **GLM check:** GLM label=negative, gold=negative
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-006  (factual, easy, phrasing: direct)
Why it is here: GLM disagrees (or no usable answer)

> What is a black hole?

- **Gold:** Reference: A black hole is a region of space where gravity is so strong that nothing, not even light, can escape once inside its event horizon; many form when massive stars collapse.
  Key points: gravity so strong light cannot escape; boundary called the event horizon
- **Note:** Reference: A black hole is a region of space where gravity is so strong that nothing, not even light, can escape once inside its event horizon; many form when massive stars collapse.
- **GLM said:** A black hole is a region of spacetime where gravity is so intense that nothing—not even light—can escape once it crosses the event horizon, the boundary beyond which escape is impossible.  Black holes typically form when massive stars (roughly 20+ times the Sun's mass) collapse at the end of their lives. They come in several types: stellar-mass black holes, supermassive black holes (millions to billions of solar masses, found at galaxy centers, like Sagittarius A* in the Milky Way), and possibly
- **GLM check:** VERDICT: FAIL
The answer invents a specific figure ("roughly 20+ times the Sun's mass") not present in the reference, violating the no-invented-numbers rule.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-013  (factual, hard, phrasing: casual)
Why it is here: GLM disagrees (or no usable answer)

> quick question - why is the speed of light central to special relativity?

- **Gold:** Reference: Special relativity postulates that the speed of light in vacuum is the same for all inertial observers, which leads to time dilation and length contraction and makes it the maximum speed at which information or matter can travel.
  Key points: constant for all inertial observers; implies time dilation and length contraction; nothing with mass can reach/exceed it
- **Note:** Reference: Special relativity postulates that the speed of light in vacuum is the same for all inertial observers, which leads to time dilation and length contraction and makes it the maximum speed at which information or matter can travel.
- **GLM said:** Because special relativity is built on two postulates: the laws of physics are the same in all inertial frames, and light travels at the same speed *c* in all inertial frames regardless of the motion of the source or observer.  That second postulate is radical. In everyday physics, speeds add — throw a ball from a moving train and the ground sees a faster ball. But light doesn't work that way: whether you chase a light beam or run toward it, you measure the same *c*.  To keep *c* constant for ev
- **GLM check:** VERDICT: FAIL
The answer covers invariance of c and time dilation/length contraction, but never states that nothing with mass can reach or exceed the speed of light.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-046  (factual, easy, phrasing: casual)
Why it is here: GLM disagrees (or no usable answer)

> quick question - what does DNS do?

- **Gold:** Reference: The Domain Name System translates human-readable domain names such as example.com into the numeric IP addresses computers use to find each other.
  Key points: translates domain names to IP addresses; works as a distributed/hierarchical lookup system
- **Note:** Reference: The Domain Name System translates human-readable domain names such as example.com into the numeric IP addresses computers use to find each other.
- **GLM said:** DNS (Domain Name System) translates human-readable domain names like `example.com` into IP addresses like `93.184.216.34` that computers use to locate each other on the internet.  Think of it as the internet's phonebook: you look up a name, and it gives you the number to connect. When you visit a website, your device queries DNS servers to resolve the domain to an IP address, then connects to that server.  It also supports related lookups, like mail server records (MX) for email routing.
- **GLM check:** VERDICT: FAIL
The answer correctly explains translation to IP addresses but never conveys that DNS is a distributed/hierarchical lookup system, so a required key point is missing.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-017  (factual, hard, phrasing: embedded)
Why it is here: random 20% sample of GLM-agreed items

> I'm writing a short explainer and I want to be sure I get this right. What was the significance of the Magna Carta of 1215?

- **Gold:** Reference: Barons forced King John to accept it, establishing that the king was subject to the law and limiting arbitrary royal power; it became a symbol and precursor of constitutional government, although its original terms mainly protected the barons' feudal rights.
  Key points: imposed on King John by barons in 1215; king subject to law / limits on royal power; precursor of constitutional rights
- **Note:** Reference: Barons forced King John to accept it, establishing that the king was subject to the law and limiting arbitrary royal power; it became a symbol and precursor of constitutional government, although its original terms mainly protected the barons' feudal rights.
- **GLM said:** The Magna Carta, sealed by King John in June 1215 at Runnymede, was a peace treaty between the king and rebellious barons. Its significance lies in establishing the principle that the monarch's power was not absolute and was subject to the law.  Key provisions included protections against unlawful imprisonment (the origin of due process ideas), limits on royal taxation without consent, and guarantees of justice "to no one will we sell, deny, or delay right or justice."  Though initially annulled
- **GLM check:** VERDICT: PASS
The candidate correctly covers all key points—barons forcing King John in 1215, the king being subject to law, and its role as a precursor of constitutional government—with accurate extra detail.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-005  (factual, hard, phrasing: casual)
Why it is here: random 20% sample of GLM-agreed items

> quick question - what is opportunity cost?

- **Gold:** Reference: Opportunity cost is the value of the next best alternative given up when a choice is made; because resources are scarce, every choice has one.
  Key points: value of the next best alternative forgone; arises from scarcity/choice
- **Note:** Reference: Opportunity cost is the value of the next best alternative given up when a choice is made; because resources are scarce, every choice has one.
- **GLM said:** Opportunity cost is the value of the next best alternative you give up when making a choice.  Example: If you spend $20 on a movie, your opportunity cost is whatever else you could have done with that $20 (and the time) — like buying a book or saving it.  It's a core economics concept because resources (money, time, effort) are limited, so every decision involves trade-offs. It includes both explicit costs (money spent) and implicit costs (benefits forgone, like wages lost while attending school
- **GLM check:** VERDICT: PASS — It correctly defines opportunity cost as the value of the next best alternative forgone and explains it arises from limited resources (scarcity), with accurate extra detail.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-027  (factual, hard, phrasing: direct)
Why it is here: random 20% sample of GLM-agreed items

> How do mRNA vaccines work?

- **Gold:** Reference: They deliver messenger RNA that instructs the body's cells to make a harmless piece of the pathogen, such as the spike protein, which the immune system learns to recognise; the mRNA is soon broken down and does not change a person's DNA.
  Key points: mRNA instructs cells to make an antigen (e.g. spike protein); immune system responds and remembers; mRNA degrades and does not alter DNA
- **Note:** Reference: They deliver messenger RNA that instructs the body's cells to make a harmless piece of the pathogen, such as the spike protein, which the immune system learns to recognise; the mRNA is soon broken down and does not change a person's DNA.
- **GLM said:** mRNA vaccines deliver lab-made messenger RNA instructions to your cells, usually encased in lipid nanoparticles for protection and delivery.  Once inside cells, ribosomes read the mRNA and build a harmless piece of the pathogen—typically the spike protein of SARS-CoV-2. Your immune system recognizes this protein as foreign, producing antibodies and training T cells against it.  The mRNA itself degrades within days and never enters the cell nucleus or alters DNA. If you later encounter the real v
- **GLM check:** VERDICT: PASS
The answer covers all three key points (cells make antigen/spike protein, immune system responds and remembers, mRNA degrades without altering DNA) with accurate extra detail.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-028  (factual, hard, phrasing: direct)
Why it is here: random 20% sample of GLM-agreed items

> Why is the sky blue and not violet?

- **Gold:** Reference: Violet is scattered even more than blue, but the Sun emits less violet light, the upper atmosphere absorbs some of it, and human eyes are less sensitive to violet, so the sky appears blue.
  Key points: violet is scattered more strongly than blue; Sun emits less violet and some is absorbed; human eyes are less sensitive to violet
- **Note:** Reference: Violet is scattered even more than blue, but the Sun emits less violet light, the upper atmosphere absorbs some of it, and human eyes are less sensitive to violet, so the sky appears blue.
- **GLM said:** The sky is blue because air molecules scatter sunlight, and shorter wavelengths scatter much more strongly (Rayleigh scattering, ~1/λ⁴). Violet light scatters even more than blue, so why isn't the sky violet?  Three reasons:  1. **The sun emits less violet than blue light**, so there's less violet to begin with. 2. **Our eyes are less sensitive to violet.** Cone cells respond most strongly to blue, green, and red; violet sits at the edge of our vision. 3. **Some violet is absorbed** in the upper
- **GLM check:** VERDICT: PASS
The candidate correctly covers all three key points: violet scatters more, the Sun emits less violet with some absorbed, and eyes are less sensitive to violet.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-008  (factual, hard, phrasing: direct)
Why it is here: random 20% sample of GLM-agreed items

> What is a hash function, and why is that useful for storing passwords?

- **Gold:** Reference: A hash function maps input of any size to a fixed-size output, is deterministic and is easy to compute but hard to reverse, so a system can store only the hash of a password (ideally salted) and compare hashes at login.
  Key points: maps input to fixed-size output deterministically; one-way: hard to invert; store hashes (with salt), not plaintext passwords
- **Note:** Reference: A hash function maps input of any size to a fixed-size output, is deterministic and is easy to compute but hard to reverse, so a system can store only the hash of a password (ideally salted) and compare hashes at login.
- **GLM said:** A hash function takes input data of any size and produces a fixed-size output (the hash) that appears random. Key properties: it's deterministic (same input → same output), infeasible to reverse, and small input changes drastically change the output.  For passwords, you store only the hash, never the plaintext. When a user logs in, you hash their entered password and compare it to the stored hash. Benefits:  - **Breach protection**: If the database is stolen, attackers get hashes, not passwords.
- **GLM check:** VERDICT: PASS
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-003  (factual, easy, phrasing: direct)
Why it is here: random 20% sample of GLM-agreed items

> What does GDP measure?

- **Gold:** Reference: Gross domestic product measures the total market value of all final goods and services produced within a country in a given period.
  Key points: total value of goods and services; produced within a country in a period
- **Note:** Reference: Gross domestic product measures the total market value of all final goods and services produced within a country in a given period.
- **GLM said:** GDP (Gross Domestic Product) measures the total monetary value of all final goods and services produced within a country's borders during a specific period, usually a quarter or year.  Key points: - It covers only **final** goods and services, avoiding double-counting of intermediate goods. - It's measured within a country's **borders**, regardless of who owns the production. - It can be calculated three ways: production (value added), income, or expenditure (C + I + G + net exports), all yieldi
- **GLM check:** VERDICT: PASS
The candidate correctly states that GDP measures the total monetary value of final goods and services produced within a country's borders during a specific period, covering all key points with accurate extra detail.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

## Batch 3 (10 items)

#### fact-009  (factual, hard, phrasing: direct)
Why it is here: random 20% sample of GLM-agreed items

> What is the difference between a recession and a depression?

- **Gold:** Reference: A recession is a significant, widespread decline in economic activity, often defined as two consecutive quarters of falling GDP; a depression is a far more severe and prolonged downturn, such as the 1930s Great Depression, and has no single official definition.
  Key points: recession: shorter/milder decline (often two quarters of falling GDP); depression: much more severe and prolonged; depression has no formal precise definition
- **Note:** Reference: A recession is a significant, widespread decline in economic activity, often defined as two consecutive quarters of falling GDP; a depression is a far more severe and prolonged downturn, such as the 1930s Great Depression, and has no single official definition.
- **GLM said:** A recession is a significant decline in economic activity—falling GDP, rising unemployment, reduced spending—typically lasting a few months to a couple of years. A depression is a more severe, prolonged downturn: much deeper GDP contraction (often 10%+), unemployment reaching 20-25%, and lasting years rather than months.  There's no precise technical definition of a depression; it's generally recognized by severity and duration. The Great Depression (1929–1939, with ~25% unemployment) is the cla
- **GLM check:** VERDICT: PASS
Covers all key points (recession milder/shorter, depression severe/prolonged, no precise definition) with accurate, commonly cited figures.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-016  (factual, hard, phrasing: casual)
Why it is here: random 20% sample of GLM-agreed items

> quick question - what is the difference between TCP and UDP?

- **Gold:** Reference: TCP is connection-oriented and provides reliable, ordered delivery using acknowledgements and retransmission; UDP is connectionless with no delivery guarantee but lower overhead and latency, so it suits streaming, gaming and DNS.
  Key points: TCP reliable, ordered, connection-oriented; UDP connectionless, no guarantees, lower latency
- **Note:** Reference: TCP is connection-oriented and provides reliable, ordered delivery using acknowledgements and retransmission; UDP is connectionless with no delivery guarantee but lower overhead and latency, so it suits streaming, gaming and DNS.
- **GLM said:** TCP (Transmission Control Protocol) is connection-oriented and reliable — it establishes a connection, guarantees delivery, orders packets, and retransmits lost ones. Used for web browsing, email, file transfers.  UDP (User Datagram Protocol) is connectionless and fast — no handshake, no delivery guarantees, no ordering. Used for streaming, gaming, VoIP, DNS, where speed matters more than reliability.  In short: TCP = reliable but slower; UDP = fast but "best effort."
- **GLM check:** VERDICT: PASS
The candidate correctly covers TCP's connection-oriented reliability and ordering, UDP's connectionless best-effort nature and lower latency, with no factual errors.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### fact-048  (factual, hard, phrasing: direct)
Why it is here: random 20% sample of GLM-agreed items

> What does the Heisenberg uncertainty principle say?

- **Gold:** Reference: It says that certain pairs of properties, such as position and momentum, cannot both be known with arbitrary precision at the same time; this is a fundamental feature of quantum systems, not just a limit of measuring instruments.
  Key points: position and momentum can't both be exactly known; fundamental to quantum mechanics, not instrument clumsiness
- **Note:** Reference: It says that certain pairs of properties, such as position and momentum, cannot both be known with arbitrary precision at the same time; this is a fundamental feature of quantum systems, not just a limit of measuring instruments.
- **GLM said:** The Heisenberg uncertainty principle states that certain pairs of physical properties of a particle—most famously position and momentum—cannot both be known with arbitrary precision at the same time. The more precisely you measure one, the less precisely you can know the other. Mathematically: Δx · Δp ≥ ℏ/2, where Δx is position uncertainty and Δp is momentum uncertainty.  This isn't a limitation of measurement instruments; it's a fundamental feature of nature arising from the wave-like behavior
- **GLM check:** VERDICT: PASS
The candidate correctly states both key points—position and momentum can't both be exactly known, and it's fundamental rather than an instrument limitation—with accurate extra detail.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-016  (summarisation, hard, phrasing: embedded)
Why it is here: GLM disagrees (or no usable answer)

> Here's an article my manager sent me. Can you summarise it in no more than 25 words? I only have a minute.
> 
> The Haldane Prize for young mathematicians was awarded this year to Imani Okafor, 27, for proving a long-standing conjecture about patterns in prime numbers. Her proof, 62 pages long and posted online in March, was checked by three independent teams over four months. Okafor said she worked on the problem during evenings while teaching school, and she plans to donate part of the 100,000 dollar prize to a programme that mentors girls in mathematics. The prize, named after a pioneering statistician, is awarded every two years to a mathematician under 30. Okafor studied at a university in Lagos and completed a doctorate in Cambridge before returning to teaching. Her result concerns the gaps between consecutive primes and builds on earlier work by several leading researchers.

- **Gold:** Constraint: `{'max_words': 25}`
  Key facts that must survive: Imani Okafor won the Haldane Prize for proving a conjecture about primes; proof checked by three teams over four months; will donate part of the 100,000 dollar prize to mentor girls
- **Note:** Constraint is checked by code; key facts (Imani Okafor won the Haldane Prize for proving a conjecture about primes; proof checked by three teams over four months; will donate part of the 100,000 dollar prize to mentor girls) must survive and nothing may be invented (blind judge).
- **GLM said:** Imani Okafor, 27, won the Haldane Prize for proving a long-standing prime number conjecture, and plans to donate part of the $100,000 prize to mentoring girls in mathematics.
- **GLM check:** VERDICT: FAIL
The candidate omits the key point that the proof was checked by three independent teams over four months.
- GLM's own summary broke the constraint (28 words, max 25): that is about GLM, not the gold.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-017  (summarisation, easy, phrasing: imperative)
Why it is here: GLM disagrees (or no usable answer)

> Summarise the following text in no more than 35 words:
> 
> The Lakeshore ferry service will be suspended for ten days in September while the pier is rebuilt. The pier has been unsafe since a crack was found in a supporting beam in March, and engineers have limited the ferry to 60 passengers per trip since then. A replacement bus will run between the two towns every 30 minutes, adding about 40 minutes to the journey. The 3.5 million pound project is paid for by the regional transport fund. The ferry carries about 2,000 passengers on a typical summer day and is popular with cyclists and hikers. Passengers with season tickets will be able to use the replacement bus at no extra charge. The pier was built in 1936, and heritage groups want the original wooden railings to be kept.

- **Gold:** Constraint: `{'max_words': 35}`
  Key facts that must survive: ferry suspended for ten days in September for pier rebuild; replacement bus every 30 minutes, adds about 40 minutes; 3.5 million pound project
- **Note:** Constraint is checked by code; key facts (ferry suspended for ten days in September for pier rebuild; replacement bus every 30 minutes, adds about 40 minutes; 3.5 million pound project) must survive and nothing may be invented (blind judge).
- **GLM said:** The Lakeshore ferry will be suspended for ten days in September for a £3.5 million pier rebuild, funded by the regional transport fund. A replacement bus will run every 30 minutes, free for season ticket holders.
- **GLM check:** VERDICT: FAIL
The candidate omits the required key point that the replacement bus adds about 40 minutes to the journey.
- GLM's own summary broke the constraint (36 words, max 35): that is about GLM, not the gold.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-021  (summarisation, easy, phrasing: imperative)
Why it is here: GLM disagrees (or no usable answer)

> Summarise the following text in no more than 35 words:
> 
> The Millbrook community garden, started in 2015 on a disused car park, now has 85 plots and a waiting list of more than 200 people. Members grow vegetables and herbs, and surplus produce is donated weekly to a food bank, which received 1.4 tonnes last year. A new greenhouse, paid for by a 12,000 pound grant, will let the garden start seedlings earlier in the year. The council has agreed to renew its lease for another ten years. The garden is run by 30 volunteers who meet every Wednesday morning, and new members pay 25 pounds a year. A beekeeping group keeps four hives on the roof of the tool shed. Schools visit in the spring term to learn about growing food, and the garden has won a regional award for community projects.

- **Gold:** Constraint: `{'max_words': 35}`
  Key facts that must survive: started in 2015 on a disused car park, 85 plots; 1.4 tonnes donated to a food bank; 12,000 pound grant pays for a new greenhouse
- **Note:** Constraint is checked by code; key facts (started in 2015 on a disused car park, 85 plots; 1.4 tonnes donated to a food bank; 12,000 pound grant pays for a new greenhouse) must survive and nothing may be invented (blind judge).
- **GLM said:** The Millbrook community garden, opened in 2015, has 85 plots, a 200-person waiting list, and donates surplus produce to a food bank. A grant-funded greenhouse is coming, the lease is renewed for ten years, and it has won a regional award.
- **GLM check:** VERDICT: FAIL
The candidate omits the 1.4 tonnes donated, the 12,000 pound grant amount, and the disused car park detail required by the key points.
- GLM's own summary broke the constraint (41 words, max 35): that is about GLM, not the gold.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-029  (summarisation, hard, phrasing: embedded)
Why it is here: GLM disagrees (or no usable answer)

> Here's an article my manager sent me. Can you summarise it in no more than 25 words? I only have a minute.
> 
> The new subway line opened on Saturday after eight years of delays. Originally budgeted at 3.2 billion dollars, it ended up costing 5.1 billion, which the transport authority blames on tunnelling through unexpected rock and on redesigns after a safety review. The line runs 17 kilometres with 14 stations and is expected to carry 200,000 riders a day. Opposition politicians called for an inquiry into the overspend, but the mayor says the project will pay back through reduced congestion. The line connects the airport in the north with the university district in the south and has a transfer to the existing blue line. Trains are driverless and run every three minutes at peak times. Tickets for the first week are free, and the transport authority expects the opening to be followed by a long period of fine-tuning.

- **Gold:** Constraint: `{'max_words': 25}`
  Key facts that must survive: line opened after eight years of delays; cost 5.1 billion dollars versus 3.2 billion budget; 17 km with 14 stations
- **Note:** Constraint is checked by code; key facts (line opened after eight years of delays; cost 5.1 billion dollars versus 3.2 billion budget; 17 km with 14 stations) must survive and nothing may be invented (blind judge).
- **GLM said:** The delayed, over-budget subway line opened Saturday: 17 km, 14 stations, 200,000 daily riders expected, free tickets first week, inquiry demanded over costs.
- **GLM check:** VERDICT: FAIL
The candidate omits the required cost figures (5.1 vs 3.2 billion) and the eight years of delays.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-032  (summarisation, easy, phrasing: imperative)
Why it is here: GLM disagrees (or no usable answer)

> Summarise the following text in no more than 35 words:
> 
> A heatwave in southern Spain pushed temperatures above 44 degrees on Thursday, a record for the month of June. Authorities issued red alerts in six provinces and asked people to avoid outdoor work between noon and 6 pm. Hospitals reported a 25 percent rise in heat-related admissions. The weather agency said the heat should ease at the weekend, when a cooler wind from the Atlantic is expected. The previous June record was 43.1 degrees, set in 2017. Several regions have banned barbecues in forests, and some outdoor events in Seville and Cordoba were postponed. Farmers say that the heat has damaged olive blossoms, and the agriculture ministry will assess the losses next week.

- **Gold:** Constraint: `{'max_words': 35}`
  Key facts that must survive: temperatures above 44 degrees, June record; red alerts in six provinces; heat should ease at the weekend
- **Note:** Constraint is checked by code; key facts (temperatures above 44 degrees, June record; red alerts in six provinces; heat should ease at the weekend) must survive and nothing may be invented (blind judge).
- **GLM said:** A record June heatwave in southern Spain exceeded 44°C, prompting red alerts in six provinces, a 25% rise in heat-related hospital admissions, barbecue bans, postponed events, and damage to olive blossoms.
- **GLM check:** VERDICT: FAIL
The candidate omits the required key point that the heat should ease at the weekend.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-037  (summarisation, easy, phrasing: tldr)
Why it is here: GLM disagrees (or no usable answer)

> Brightfield Bakery announced on Monday that it will close its three smaller shops by the end of June and focus on its main store and online orders. The owner, Maria Castillo, said rising flour and energy costs had cut profits by almost half since 2022. Around 14 employees will be offered jobs at the main store or at a partner cafe. Customers will be able to order the bakery's best-selling sourdough for nationwide delivery from July. The bakery was founded in 1987 by Castillo's parents and became known for its cinnamon rolls and rye loaves. Its smaller shops are in two suburbs and a railway station, and the rents on those sites rose sharply last year. Castillo said she would keep the recipes unchanged and thanked customers for their loyalty.
> 
> TL;DR in exactly one sentence, please.

- **Gold:** Constraint: `{'sentences': 1}`
  Key facts that must survive: closing three smaller shops by end of June; rising flour and energy costs halved profits; focus on main store and online orders
- **Note:** Constraint is checked by code; key facts (closing three smaller shops by end of June; rising flour and energy costs halved profits; focus on main store and online orders) must survive and nothing may be invented (blind judge).
- **GLM said:** Brightfield Bakery will close its three smaller shops by the end of June due to rising costs, moving affected employees to its main store or a partner cafe while continuing nationwide online delivery of its sourdough from July.
- **GLM check:** VERDICT: FAIL
It omits the key point that the bakery will focus on its main store and online orders, only mentioning employee relocation and sourdough delivery.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-038  (summarisation, easy, phrasing: tldr)
Why it is here: GLM disagrees (or no usable answer)

> The government has announced a plan to give 1.2 million households a one-off payment of 150 pounds towards winter heating bills. The payment will be made automatically in November to people receiving certain benefits, and the 180 million pound cost will come from existing budgets. Charities welcomed the move but said it is smaller than last year's help and does not reach many pensioners on low incomes. Last year's payment was 300 pounds and reached 2.4 million households, which is why charities say this year's scheme is less generous. Energy prices have fallen 22 percent since the peak, but remain well above levels from before 2021. The finance minister said the government would keep the policy under review.
> 
> TL;DR in no more than 35 words, please.

- **Gold:** Constraint: `{'max_words': 35}`
  Key facts that must survive: 150 pound one-off payment to 1.2 million households; paid in November, 180 million pounds; charities say it is smaller and misses some pensioners
- **Note:** Constraint is checked by code; key facts (150 pound one-off payment to 1.2 million households; paid in November, 180 million pounds; charities say it is smaller and misses some pensioners) must survive and nothing may be invented (blind judge).
- **GLM said:** The government will pay 1.2 million benefit-claiming households £150 toward winter heating bills in November, funded from existing budgets. Charities welcomed it but noted it's smaller than last year's £300 payment.
- **GLM check:** VERDICT: FAIL
The candidate omits the required 180 million pound cost detail.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

## Batch 4 (10 items)

#### summ-040  (summarisation, hard, phrasing: imperative)
Why it is here: GLM disagrees (or no usable answer)

> Summarise the following text in no more than 25 words:
> 
> The Ferris Valley railway, closed in 1966, will partly reopen next year after a campaign by local residents raised 2.5 million pounds. Only 9 of the original 24 kilometres will carry trains at first, run by volunteers using restored steam locomotives at weekends. A further 4 million pounds is needed to rebuild a collapsed bridge before the full line can reopen. Organisers expect the heritage line to bring 60,000 tourists a year to the valley. The Ferris Valley line was closed in 1966 as part of national cuts to rural railways, and its tracks lay overgrown for 30 years before volunteers began clearing them. The reopened stretch will have two stations and a small museum. The campaign group, founded in 2008, has about 1,200 members and receives no government funding.

- **Gold:** Constraint: `{'max_words': 25}`
  Key facts that must survive: railway closed in 1966 partly reopens next year; 9 of 24 km, volunteers run steam trains; 4 million more needed for the bridge
- **Note:** Constraint is checked by code; key facts (railway closed in 1966 partly reopens next year; 9 of 24 km, volunteers run steam trains; 4 million more needed for the bridge) must survive and nothing may be invented (blind judge).
- **GLM said:** The partly volunteer-run Ferris Valley heritage railway reopens next year after residents raised £2.5 million; £4 million more is needed to reopen the full line.
- **GLM check:** VERDICT: FAIL
It omits the key point that only 9 of the original 24 km will carry trains run by volunteers using steam locomotives.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-047  (summarisation, hard, phrasing: embedded)
Why it is here: GLM disagrees (or no usable answer)

> Here's an article my manager sent me. Can you summarise it in no more than 25 words? I only have a minute.
> 
> Candidates for next month's election in Norvia debated on live television for the first time on Wednesday. Incumbent president Sara Voss defended her record of cutting unemployment from 8 to 5 percent, while challenger Tomas Rhee argued that wages have not kept up with prices and promised to raise the minimum wage by 12 percent. A poll taken after the debate gave Voss 46 percent and Rhee 44 percent, within the margin of error of 3 points, with 10 percent undecided. Norvia has 11 million voters and has been governed by a centre-left coalition since 2019. The debate lasted 90 minutes and was moderated by two journalists. Two other candidates, from the Green party and a small conservative movement, were not invited because their polling is below 5 percent.

- **Gold:** Constraint: `{'max_words': 25}`
  Key facts that must survive: Voss and Rhee debated; Voss cites unemployment cut from 8 to 5 percent; Rhee promises a 12 percent minimum wage rise; poll 46 to 44 percent, within margin of error
- **Note:** Constraint is checked by code; key facts (Voss and Rhee debated; Voss cites unemployment cut from 8 to 5 percent; Rhee promises a 12 percent minimum wage rise; poll 46 to 44 percent, within margin of error) must survive and nothing may be invented (blind judge).
- **GLM said:** In Norvia's first televised election debate, incumbent Voss defended her record while challenger Rhee promised wage rises; a post-debate poll shows them statistically tied.
- **GLM check:** VERDICT: FAIL, the candidate omits the specific key points: the 8-to-5 percent unemployment cut, the 12 percent minimum wage rise, and the 46–44 poll figures.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-049  (summarisation, easy, phrasing: careful)
Why it is here: GLM disagrees (or no usable answer)

> Condense this passage in exactly one sentence. Keep only facts stated in the text.
> 
> "Parents at Greenway Primary School have voted to ban phones from the playground. In a ballot of 312 families, 71 percent supported the ban, which starts after the winter break. Teachers say pupils spend break times looking at screens instead of playing, and the head teacher hopes the rule will reduce arguments linked to social media. Children who need a phone to travel home can hand it in at the office in the morning. The school has 480 pupils aged four to eleven. Staff already ask children to keep phones in their bags during lessons, but they say rules were hard to enforce during breaks. The head teacher said the ban would be reviewed after one term, and parents who disagreed were invited to a meeting in January."

- **Gold:** Constraint: `{'sentences': 1}`
  Key facts that must survive: parents voted to ban phones from the playground; 71 percent of 312 families supported; phones can be handed in at the office
- **Note:** Constraint is checked by code; key facts (parents voted to ban phones from the playground; 71 percent of 312 families supported; phones can be handed in at the office) must survive and nothing may be invented (blind judge).
- **GLM said:** Parents at Greenway Primary School voted 71 percent in favor of banning phones from the playground starting after the winter break, with exceptions for children who need a phone to travel home, and the head teacher said the ban would be reviewed after one term.
- **GLM check:** VERDICT: FAIL
The candidate omits two required key points: the 312 families figure and the option to hand phones in at the office.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-007  (summarisation, easy, phrasing: careful)
Why it is here: random 20% sample of GLM-agreed items

> Condense this passage in exactly one sentence. Keep only facts stated in the text.
> 
> "A software update released on Tuesday fixes a security flaw that could let attackers read messages sent through the Chatly app. The flaw, found by an independent researcher, affected versions released since September and was present on both phones and computers. Chatly says it has seen no evidence that the weakness was used. Users should install version 5.3 as soon as possible; the update downloads automatically if automatic updates are switched on. Chatly has 40 million monthly users in 90 countries and is known for its group chats and disappearing messages. The security researcher who found the flaw was paid a reward of 15,000 dollars under the company's bug-bounty programme. Chatly said it will publish a full technical explanation in two weeks."

- **Gold:** Constraint: `{'sentences': 1}`
  Key facts that must survive: update fixes a security flaw in Chatly; install version 5.3; no evidence the flaw was exploited
- **Note:** Constraint is checked by code; key facts (update fixes a security flaw in Chatly; install version 5.3; no evidence the flaw was exploited) must survive and nothing may be invented (blind judge).
- **GLM said:** Chatly's Tuesday software update (version 5.3) fixes a security flaw found by an independent researcher—who received a 15,000-dollar bug-bounty reward—that affected versions since September on both phones and computers and could have let attackers read Chatly messages, though the company says it has seen no evidence of exploitation and urges its 40 million monthly users in 90 countries to install the update, which downloads automatically if automatic updates are on, and says it will publish a fu
- **GLM check:** VERDICT: PASS
The candidate correctly covers all key points (update fixes flaw, version 5.3, no evidence of exploitation) with no invented facts.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-031  (summarisation, hard, phrasing: imperative)
Why it is here: random 20% sample of GLM-agreed items

> Summarise the following text in exactly two sentences:
> 
> A fire at the Brantley warehouse on Tuesday night destroyed about 2 million dollars worth of electronics. Firefighters from five stations took six hours to bring the blaze under control, and 18 nearby homes were evacuated as a precaution but residents returned the next morning. Investigators say the fire started near a charging area for forklift batteries, although the exact cause is still unknown. No one was injured, and the company says it will reopen a smaller site within a month. The warehouse, built in 2004, stood in an industrial park on the edge of town and stored televisions, laptops and phone accessories for several retailers. Smoke could be seen from 20 kilometres away, and the main road was closed for most of the night. Insurance assessors will visit the site later this week.

- **Gold:** Constraint: `{'sentences': 2}`
  Key facts that must survive: fire destroyed about 2 million dollars of electronics; 18 homes evacuated, no one injured; started near forklift battery charging area, cause unknown
- **Note:** Constraint is checked by code; key facts (fire destroyed about 2 million dollars of electronics; 18 homes evacuated, no one injured; started near forklift battery charging area, cause unknown) must survive and nothing may be invented (blind judge).
- **GLM said:** A fire at the Brantley warehouse on Tuesday night destroyed about 2 million dollars worth of electronics, taking firefighters from five stations six hours to control while 18 nearby homes were evacuated as a precaution. No one was injured, and although investigators believe the fire started near a forklift battery charging area, the exact cause remains unknown; the company plans to reopen a smaller site within a month.
- **GLM check:** VERDICT: PASS
All three key points are accurately covered with no contradictions or invented facts.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-004  (summarisation, hard, phrasing: imperative)
Why it is here: random 20% sample of GLM-agreed items

> Summarise the following text as exactly 3 bullet points (each line starting with '- '):
> 
> Wildlife officials counted 3,200 snow leopards across Central Asia in a five-year survey, up from an estimate of 2,500 a decade ago. Conservationists credit community programmes that pay herders compensation for livestock lost to leopards, which has reduced revenge killings by about half in surveyed valleys. However, the survey used camera traps in only 40 percent of the range, and some experts believe the apparent rise may partly reflect better counting methods rather than a real increase. Climate change is shrinking the high-altitude habitat the animals depend on. Snow leopards live in 12 countries at altitudes up to 5,500 metres and are very hard to spot, which is why researchers rely on camera traps and droppings. They are listed as vulnerable. The survey was coordinated by a conservation coalition and took five years, covering about 1.2 million square kilometres.

- **Gold:** Constraint: `{'bullets': 3}`
  Key facts that must survive: 3,200 snow leopards counted, up from 2,500; herder compensation halved revenge killings; counting may overstate the rise; climate change shrinks habitat
- **Note:** Constraint is checked by code; key facts (3,200 snow leopards counted, up from 2,500; herder compensation halved revenge killings; counting may overstate the rise; climate change shrinks habitat) must survive and nothing may be invented (blind judge).
- **GLM said:** - A five-year survey counted 3,200 snow leopards across Central Asia, up from an estimated 2,500 a decade ago, with conservationists crediting compensation programmes for herders that cut revenge killings by about half. - Experts caution the rise may partly reflect better counting methods, as camera traps covered only 40 percent of the range, and climate change is shrinking the species' high-altitude habitat. - Snow leopards live in 12 countries at altitudes up to 5,500 metres, are listed as vul
- **GLM check:** VERDICT: PASS
The candidate accurately covers all key points (3,200 vs 2,500, halved revenge killings via compensation, possible overcounting and shrinking habitat) with no invented facts.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-002  (summarisation, hard, phrasing: imperative)
Why it is here: random 20% sample of GLM-agreed items

> Summarise the following text in exactly two sentences:
> 
> Last week the central bank held its main interest rate at 4.5 percent, surprising some economists who had expected a cut. Governor Lena Karlsson said inflation, now at 3.1 percent, is falling but remains above the 2 percent target, and that wage growth of 5.4 percent could keep prices rising. Markets now expect the first cut in September rather than June. Mortgage lenders said the decision means borrowers on variable-rate deals will see no relief for several months. The governor spoke at a press conference in the capital on Thursday after a vote of seven to two within the monetary policy committee. The bank raised rates eleven times between 2022 and 2023 to deal with an inflation peak above 9 percent. The currency strengthened slightly against the dollar after the announcement.

- **Gold:** Constraint: `{'sentences': 2}`
  Key facts that must survive: central bank held its rate at 4.5 percent; inflation 3.1 percent above 2 percent target; wage growth 5.4 percent; first cut now expected in September
- **Note:** Constraint is checked by code; key facts (central bank held its rate at 4.5 percent; inflation 3.1 percent above 2 percent target; wage growth 5.4 percent; first cut now expected in September) must survive and nothing may be invented (blind judge).
- **GLM said:** The central bank held its main interest rate at 4.5 percent, surprising economists who expected a cut, as Governor Lena Karlsson said inflation at 3.1 percent remains above the 2 percent target and wage growth of 5.4 percent could keep prices rising. Markets now expect the first cut in September rather than June, meaning variable-rate borrowers will see no relief for several months.
- **GLM check:** VERDICT: PASS
All three key points are accurately covered with no invented facts or contradictions.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-044  (summarisation, hard, phrasing: embedded)
Why it is here: random 20% sample of GLM-agreed items

> Here's an article my manager sent me. Can you summarise it in exactly two sentences? I only have a minute.
> 
> The Marsden Foundation announced a 12 million dollar scholarship fund for students from rural areas, to be distributed over five years. Each scholarship covers tuition and a living allowance of 8,000 dollars a year for up to four years, and about 300 students are expected to benefit in total. Applicants must show financial need and have grown up at least 50 kilometres from a major city. The foundation says it chose the criteria after finding that rural students are 40 percent less likely to attend university than urban peers. The foundation was set up by a retired shipping executive, Elias Marsden, in 1998 and has already given away 60 million dollars to education projects. Applications open in January and will be judged by a panel of university representatives. Scholarship holders may study at any accredited public university in the country.

- **Gold:** Constraint: `{'sentences': 2}`
  Key facts that must survive: 12 million dollar scholarship fund over five years; covers tuition and an 8,000 dollar yearly allowance for about 300 students; rural students 40 percent less likely to attend university
- **Note:** Constraint is checked by code; key facts (12 million dollar scholarship fund over five years; covers tuition and an 8,000 dollar yearly allowance for about 300 students; rural students 40 percent less likely to attend university) must survive and nothing may be invented (blind judge).
- **GLM said:** The Marsden Foundation has announced a 12 million dollar scholarship fund for rural students, distributed over five years, covering tuition plus an 8,000 dollar annual living allowance for up to four years, with about 300 students expected to benefit. Applicants must demonstrate financial need and have grown up at least 50 kilometres from a major city, as the foundation found rural students are 40 percent less likely to attend university than urban peers; applications open in January and will be
- **GLM check:** VERDICT: PASS
The candidate correctly includes all three key points (12 million over five years, tuition plus 8,000 dollar allowance for about 300 students, 40 percent statistic) with no contradictions or invented facts.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-041  (summarisation, hard, phrasing: imperative)
Why it is here: random 20% sample of GLM-agreed items

> Summarise the following text in exactly two sentences:
> 
> The first successful kidney transplant took place in Boston in 1954, between identical twins, which avoided rejection because the donor and recipient were genetically the same. Surgeon Joseph Murray received the Nobel Prize in 1990 for the work. The breakthrough for unrelated donors came in the 1980s with the drug cyclosporine, which suppresses the immune system more precisely than earlier medicines. Today more than 90,000 kidney transplants are performed worldwide each year, though the waiting list is far longer. The surgeon's patient, Richard Herrick, survived for eight more years with the transplanted kidney, and the donor, his twin Ronald, lived a long life too. Dialysis, which cleans the blood with a machine, was already available in the 1950s but is a burden for patients. Many countries now run organ donation registers.

- **Gold:** Constraint: `{'sentences': 2}`
  Key facts that must survive: first kidney transplant in 1954 between identical twins; cyclosporine in the 1980s enabled transplants from unrelated donors; more than 90,000 transplants a year, waiting list longer
- **Note:** Constraint is checked by code; key facts (first kidney transplant in 1954 between identical twins; cyclosporine in the 1980s enabled transplants from unrelated donors; more than 90,000 transplants a year, waiting list longer) must survive and nothing may be invented (blind judge).
- **GLM said:** The first successful kidney transplant, performed in Boston in 1954 between identical twins Richard and Ronald Herrick, avoided rejection because the donor and recipient were genetically identical, earning surgeon Joseph Murray a Nobel Prize in 1990. The 1980s introduction of cyclosporine, which suppresses the immune system more precisely than earlier drugs, enabled transplants from unrelated donors, and today more than 90,000 kidney transplants are performed worldwide each year.
- **GLM check:** VERDICT: PASS
All three key points are present and factually consistent with the reference, with no invented details.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### summ-005  (summarisation, easy, phrasing: embedded)
Why it is here: random 20% sample of GLM-agreed items

> Here's an article my manager sent me. Can you summarise it in exactly one sentence? I only have a minute.
> 
> The old Corbett Mill, built in 1862, will reopen next spring as a museum of industrial history after a 6 million pound restoration. The project is funded mainly by a heritage lottery grant covering 4.2 million pounds, with the rest raised by donations. Visitors will see working looms, restored steam engines and recordings of former mill workers. The museum expects 80,000 visitors in its first year. The mill once employed 900 people and produced woollen cloth that was exported across Europe. It closed in 1971 and stood empty for decades, and a fire in 1998 damaged one wing. The new museum will include a cafe in the former boiler house and a classroom space for school visits, which will be free of charge.

- **Gold:** Constraint: `{'sentences': 1}`
  Key facts that must survive: Corbett Mill reopens as a museum of industrial history; 6 million pound restoration, 4.2 million from a heritage lottery grant
- **Note:** Constraint is checked by code; key facts (Corbett Mill reopens as a museum of industrial history; 6 million pound restoration, 4.2 million from a heritage lottery grant) must survive and nothing may be invented (blind judge).
- **GLM said:** The 1862 Corbett Mill, closed since 1971, will reopen next spring as a 6-million-pound industrial history museum—funded mainly by a 4.2-million-pound heritage lottery grant—featuring working looms, restored steam engines, worker recordings, a cafe, and free school classroom space, with 80,000 visitors expected in its first year.
- **GLM check:** VERDICT: PASS
The candidate correctly states the reopening as an industrial history museum and the 6-million-pound restoration with 4.2 million from the heritage lottery grant, with no contradictions or invented facts.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

## Batch 5 (10 items)

#### summ-013  (summarisation, hard, phrasing: tldr)
Why it is here: random 20% sample of GLM-agreed items

> A report on remote work surveyed 5,000 employees at 120 companies. Workers who spent three days a week at home reported 12 percent higher job satisfaction than those who were fully in the office, and their managers rated their productivity as unchanged. However, junior staff who worked remotely more than four days a week were 20 percent less likely to be promoted within two years, which the authors attribute to fewer chances to be noticed and mentored. The report recommends hybrid schedules with scheduled in-person days for new hires. The survey was run by an independent research firm in 2023 and covered workers in finance, technology and healthcare administration. Average commuting time saved was 54 minutes a day. The authors noted that results may differ in jobs where workers must be present, and that only 8 percent of respondents were in management.
> 
> TL;DR as exactly 3 bullet points (each line starting with '- '), please.

- **Gold:** Constraint: `{'bullets': 3}`
  Key facts that must survive: three remote days a week raised satisfaction by 12 percent with unchanged productivity; juniors working remotely over four days were 20 percent less likely to be promoted; recommends hybrid schedules with in-person days for new hires
- **Note:** Constraint is checked by code; key facts (three remote days a week raised satisfaction by 12 percent with unchanged productivity; juniors working remotely over four days were 20 percent less likely to be promoted; recommends hybrid schedules with in-person days for new hires) must survive and nothin
- **GLM said:** - Employees working three days a week from home reported 12 percent higher job satisfaction than fully in-office workers, with managers rating their productivity as unchanged. - Junior staff remote more than four days a week were 20 percent less likely to be promoted within two years, attributed to fewer chances to be noticed and mentored. - The 2023 survey of 5,000 employees at 120 companies recommends hybrid schedules with scheduled in-person days for new hires, noting results may differ in pr
- **GLM check:** VERDICT: PASS
All three key points are accurately covered with no invented facts or contradictions.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-003  (ner, hard, phrasing: casual)
Why it is here: hand-written NER: gold depends on the stated span conventions

> who/what/where/when is mentioned here? list the entities and their types: "Tata Consultancy Services hired Anand Rajan in Bengaluru on 1 June 2020."

- **Gold:** Tata Consultancy Services = ORG; Anand Rajan = PERSON; Bengaluru = LOCATION; 1 June 2020 = DATE
- **Note:** Organisation named after a family name.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-004  (ner, hard, phrasing: embedded)
Why it is here: hand-written NER: gold depends on the stated span conventions

> Here's a line from a news article:
> 
> Amazon expanded its warehouse network along the Amazon River in 2021.
> 
> Pull out every person, organisation, location and date it mentions, with the type of each.

- **Gold:** Amazon = ORG; Amazon River = LOCATION; 2021 = DATE
- **Note:** Company vs river with the same word.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-005  (ner, hard, phrasing: imperative)
Why it is here: hand-written NER: gold depends on the stated span conventions

> Tag the people, organisations, places and dates in this sentence: Georgia Smith moved from Georgia to Paris in March 2015.

- **Gold:** Georgia Smith = PERSON; Georgia = LOCATION; Paris = LOCATION; March 2015 = DATE
- **Note:** First name that is also a place name.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-006  (ner, hard, phrasing: embedded)
Why it is here: hand-written NER: gold depends on the stated span conventions

> Here's a line from a news article:
> 
> Siemens Energy and BP agreed terms with Kenya's government in Nairobi on 2020-11-04.
> 
> Pull out every person, organisation, location and date it mentions, with the type of each.

- **Gold:** Siemens Energy = ORG; BP = ORG; Kenya = LOCATION; Nairobi = LOCATION; 2020-11-04 = DATE
- **Note:** ISO-formatted date; 'government' is not a named entity.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-007  (ner, hard, phrasing: imperative)
Why it is here: hand-written NER: gold depends on the stated span conventions

> Tag the people, organisations, places and dates in this sentence: Jordan Peterson met Jordan's king in Amman.

- **Gold:** Jordan Peterson = PERSON; Jordan = LOCATION; Amman = LOCATION
- **Note:** 'Jordan' is a person's name in the first span and the country in the second; possessive 's is not part of the span.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-008  (ner, hard, phrasing: instruction)
Why it is here: hand-written NER: gold depends on the stated span conventions

> Extract all named entities with their types (PERSON, ORG, LOCATION, DATE) from: 'Dr. Kavita Rao of AIIMS Delhi presented the findings in Geneva on 12 May 2021.'

- **Gold:** Kavita Rao = PERSON; AIIMS Delhi = ORG; Geneva = LOCATION; 12 May 2021 = DATE
- **Note:** Title 'Dr.' is excluded from the PERSON span (stated convention); 'AIIMS Delhi' is one ORG span.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-012  (ner, hard, phrasing: embedded)
Why it is here: hand-written NER: gold depends on the stated span conventions

> Here's a line from a news article:
> 
> The Delhi Capitals beat the Mumbai Indians in Dubai on 5 April 2022.
> 
> Pull out every person, organisation, location and date it mentions, with the type of each.

- **Gold:** Delhi Capitals = ORG; Mumbai Indians = ORG; Dubai = LOCATION; 5 April 2022 = DATE
- **Note:** Sports teams named after cities are ORG; the whole team name is one span.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-014  (ner, hard, phrasing: embedded)
Why it is here: hand-written NER: gold depends on the stated span conventions

> Here's a line from a news article:
> 
> Mount Kilimanjaro in Tanzania was climbed by Amina Yusuf in January 2022.
> 
> Pull out every person, organisation, location and date it mentions, with the type of each.

- **Gold:** Mount Kilimanjaro = LOCATION; Tanzania = LOCATION; Amina Yusuf = PERSON; January 2022 = DATE
- **Note:** Mountain with a title-like prefix is one LOCATION span.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-016  (ner, hard, phrasing: casual)
Why it is here: hand-written NER: gold depends on the stated span conventions

> who/what/where/when is mentioned here? list the entities and their types: "The World Health Organization, headquartered in Geneva, praised Kerala's response in 2021."

- **Gold:** World Health Organization = ORG; Geneva = LOCATION; Kerala = LOCATION; 2021 = DATE
- **Note:** 'the' is excluded from the ORG span; possessive stripped from Kerala.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

## Batch 6 (6 items)

#### ner-020  (ner, hard, phrasing: casual)
Why it is here: hand-written NER: gold depends on the stated span conventions

> who/what/where/when is mentioned here? list the entities and their types: "Washington crossed the Delaware, according to historian Eric Foner of Columbia University."

- **Gold:** Washington = PERSON; Delaware = LOCATION; Eric Foner = PERSON; Columbia University = ORG
- **Note:** 'Washington' here is the general (a person), not the city or state.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-023  (ner, hard, phrasing: casual)
Why it is here: hand-written NER: gold depends on the stated span conventions

> who/what/where/when is mentioned here? list the entities and their types: "On 15 August 1947, Jawaharlal Nehru addressed the nation from Delhi."

- **Gold:** 15 August 1947 = DATE; Jawaharlal Nehru = PERSON; Delhi = LOCATION
- **Note:** Date at the start of the sentence.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-024  (ner, hard, phrasing: casual)
Why it is here: hand-written NER: gold depends on the stated span conventions

> who/what/where/when is mentioned here? list the entities and their types: "Lionel Messi joined Inter Miami in July 2023 after leaving Paris Saint-Germain."

- **Gold:** Lionel Messi = PERSON; Inter Miami = ORG; July 2023 = DATE; Paris Saint-Germain = ORG
- **Note:** Club names contain place names but are ORG as whole spans.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-027  (ner, hard, phrasing: imperative)
Why it is here: hand-written NER: gold depends on the stated span conventions

> Tag the people, organisations, places and dates in this sentence: Ford announced that Henry Ford's grandson would visit Detroit in 2019.

- **Gold:** Ford = ORG; Henry Ford = PERSON; Detroit = LOCATION; 2019 = DATE
- **Note:** Same surname as company and person; the company 'Ford' is the subject of the announcement.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-036  (ner, hard, phrasing: embedded)
Why it is here: hand-written NER: gold depends on the stated span conventions

> Here's a line from a news article:
> 
> Nokia, founded in Finland, is now headquartered in Espoo.
> 
> Pull out every person, organisation, location and date it mentions, with the type of each.

- **Gold:** Nokia = ORG; Finland = LOCATION; Espoo = LOCATION
- **Note:** Appositive clause between commas.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

#### ner-049  (ner, hard, phrasing: casual)
Why it is here: hand-written NER: gold depends on the stated span conventions

> who/what/where/when is mentioned here? list the entities and their types: "Apple's iPhone sales in India rose after Tim Cook visited Mumbai in April 2023."

- **Gold:** Apple = ORG; India = LOCATION; Tim Cook = PERSON; Mumbai = LOCATION; April 2023 = DATE
- **Note:** Product name 'iPhone' is not one of the four types, so it is not tagged.
- **Decision:** `[ ] gold OK   [ ] change gold to: ______   [ ] rewrite/drop item`

