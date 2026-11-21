# Judge calibration sheet (Phase 2, D8)

40 answers from small local models. For each, write **PASS** or **FAIL** after `Label:`. Model names and judge verdicts are hidden on purpose.

> **Labels relabelled under rule D10 (docs/DESIGN_DECISIONS.md), 2026-11-20:** summaries = both core facts present and nothing wrong; factual = strict. Items 8, 13, 17, 27, 28, 31 decided by Kabir; the other labels were agreed by Kabir after review.
> **Original draft note:** every `Label:` below was drafted by Claude (parent session) without looking at the judges' verdicts, and is pending Kabir's item-by-item check. Format: the first word after `Label:` is the verdict (PASS/FAIL); the rest is the reason. Kabir: change any verdict you disagree with, then add `Checked by Kabir` to this note. **Checked by Kabir (2026-11-20).**

**Rubric (same as the judges').** FAIL only if the answer states something wrong or that contradicts the reference/source, or if a REQUIRED point is missing. Correct extra detail never fails. OPTIONAL points never decide. Ignore style and length (summary length/format limits are already checked by code).

---

## Item 1  (summary)

**Task given to the model:**
> Here's an article my manager sent me. Can you summarise it in no more than 25 words? I only have a minute. ...

**Source text:**
> Candidates for next month's election in Norvia debated on live television for the first time on Wednesday. Incumbent president Sara Voss defended her record of cutting unemployment from 8 to 5 percent, while challenger Tomas Rhee argued that wages have not kept up with prices and promised to raise the minimum wage by 12 percent. A poll taken after the debate gave Voss 46 percent and Rhee 44 percent, within the margin of error of 3 points, with 10 percent undecided. Norvia has 11 million voters and has been governed by a centre-left coalition since 2019. The debate lasted 90 minutes and was moderated by two journalists. Two other candidates, from the Green party and a small conservative movement, were not invited because their polling is below 5 percent.

**Constraint (already verified OK):** {'max_words': 25}

**REQUIRED facts (each must be in the summary):**
- Voss cites unemployment cut from 8 to 5 percent
- Rhee promises a 12 percent minimum wage rise

**Candidate answer:**

> Candidates debated for first time, Voss led 46-44, poll shows 10% undecided, election in Norvia.

**Label:** FAIL — *(Claude draft, to be checked by Kabir)* misses both required facts (8→5% unemployment cut, 12% minimum-wage rise); only gives the poll

---

## Item 2  (summary)

**Task given to the model:**
> Summarise the following text as exactly 3 bullet points (each line starting with '- '): ...

**Source text:**
> Engineers at the Marlow Institute have built a robot that sorts household waste using cameras and a trained neural network. In a pilot at a recycling plant, it identified plastics, metals and paper with 94 percent accuracy and processed 60 items per minute, compared with about 35 for a human worker. The machine struggles with dirty or crushed items, where accuracy falls to 71 percent. Each unit costs 180,000 euros, so the plant expects to recoup its investment only after about five years. The institute, based in Bavaria, has 300 researchers and works with industry on automation. The robot uses a vacuum gripper and a conveyor belt and was trained on 2 million labelled images of waste. The pilot ran for three months at a plant that processes 30,000 tonnes of recyclables a year.

**Constraint (already verified OK):** {'bullets': 3}

**REQUIRED facts (each must be in the summary):**
- robot sorts waste with 94 percent accuracy at 60 items/minute
- accuracy falls to 71 percent for dirty or crushed items
- costs 180,000 euros, payback about five years

**Candidate answer:**

> *   Marlow Institute engineers created a robot for household waste sorting.
> *   The robot achieved 94% accuracy in identifying plastics, metals, and paper.
> *   It processed 60 items per minute, significantly faster than a human worker.

**Label:** FAIL — *(Claude draft, D10 rule; checked with Kabir)* one-sided: core 'but' (accuracy falls to 71% for dirty/crushed items) missing; cost also missing

---

## Item 3  (summary)

**Task given to the model:**
> Summarise the following text in exactly two sentences: ...

**Source text:**
> A fire at the Brantley warehouse on Tuesday night destroyed about 2 million dollars worth of electronics. Firefighters from five stations took six hours to bring the blaze under control, and 18 nearby homes were evacuated as a precaution but residents returned the next morning. Investigators say the fire started near a charging area for forklift batteries, although the exact cause is still unknown. No one was injured, and the company says it will reopen a smaller site within a month. The warehouse, built in 2004, stood in an industrial park on the edge of town and stored televisions, laptops and phone accessories for several retailers. Smoke could be seen from 20 kilometres away, and the main road was closed for most of the night. Insurance assessors will visit the site later this week.

**Constraint (already verified OK):** {'sentences': 2}

**REQUIRED facts (each must be in the summary):**
- fire destroyed about 2 million dollars of electronics
- 18 homes evacuated, no one injured
- started near forklift battery charging area, cause unknown

**Candidate answer:**

> A fire at the Brantley warehouse destroyed approximately $2 million worth of electronics, which was quickly brought under control by firefighters.  The warehouse, built in 2004, will reopen a smaller site within a month after investigators determine the cause of the blaze.

**Label:** FAIL — *(Claude draft, to be checked by Kabir)* misses '18 homes evacuated, no one injured' and the forklift-charging cause; 'quickly brought under control' contradicts the six hours

---

## Item 4  (summary)

**Task given to the model:**
> Summarise the following text in exactly two sentences: ...

**Source text:**
> Farmers in the Valdoro region have begun using drones to spray vineyards, replacing tractors that compact the soil on steep slopes. Each drone covers 20 hectares in a day, about four times the speed of a worker on foot, and cuts pesticide use by 30 percent because it targets only affected vines. The drones cost 25,000 euros each, and a regional subsidy covers half. Union leaders worry that the technology will remove seasonal jobs, while growers say they are short of workers. Valdoro is a wine region of about 12,000 hectares known for its steep terraced vineyards. The drones fly at a height of three metres and are guided by maps made from aerial photographs. Regulations require a licensed pilot for each flight, and a training course for growers starts next month.

**Constraint (already verified OK):** {'sentences': 2}

**REQUIRED facts (each must be in the summary):**
- drones spray vineyards: 20 hectares a day and 30 percent less pesticide
- cost 25,000 euros with a subsidy covering half
- union fears about seasonal jobs versus growers' labour shortage

**Candidate answer:**

> Farmers in Valdoro are using drones to spray vineyards, replacing tractors and reducing pesticide use by 30 percent, while the technology may lead to job losses. The drones cost 25,000 euros each, and a regional subsidy covers half the cost, but union leaders and growers are concerned about the impact on employment.

**Label:** FAIL — *(Claude draft, to be checked by Kabir)* misses '20 hectares a day'; says growers are worried about jobs, but the text says growers are short of workers (contradiction)

---

## Item 5  (factual)

**Question:**
> What does GDP measure?

**Reference answer:** Gross domestic product measures the total market value of all final goods and services produced within a country in a given period.

**REQUIRED points:**
- total value of goods and services
- produced within a country in a period

**Candidate answer:**

> GDP measures the total value of all goods and services produced in an economy over a specific period. It reflects the economic output of a country.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* total value of goods and services, produced in a country over a period

---

## Item 6  (factual)

**Question:**
> Why is the sky blue and not violet?

**Reference answer:** Violet is scattered even more than blue, but the Sun emits less violet light, the upper atmosphere absorbs some of it, and human eyes are less sensitive to violet, so the sky appears blue.

**REQUIRED points:**
- violet is scattered more strongly than blue
- Sun emits less violet and some is absorbed
- human eyes are less sensitive to violet

**Candidate answer:**

> The sky appears blue due to a phenomenon called Rayleigh scattering. Sunlight is made up of all colors of the spectrum. As sunlight enters the Earth’s atmosphere, it collides with tiny air molecules. Blue and violet light have shorter wavelengths and are scattered more effectively than other colors. 
> 
> Violet light is scattered even more than blue, but our eyes are more sensitive to blue.  Therefore, we perceive the sky as blue. 
> 
> While violet is scattered more, the sun emits less violet light, and our eyes are more attuned to blue.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* violet scattered more ✓, Sun emits less violet ✓ (the 'some is absorbed' half is missing; lenient call), eyes favour blue ✓. Borderline

---

## Item 7  (factual)

**Question:**
> What was the Cold War?

**Reference answer:** The Cold War was a period of geopolitical rivalry between the United States and the Soviet Union and their allies after World War II, fought through an arms race and proxy conflicts rather than direct war, ending around 1991.

**REQUIRED points:**
- US vs Soviet Union rivalry after WWII
- no direct full-scale war (arms race, proxy wars)

**OPTIONAL points:**
- ended around 1991

**Candidate answer:**

> The Cold War was a geopolitical struggle between the United States and the Soviet Union and their respective allies from the mid-1940s to the early 1990s. It wasn’t a direct military conflict, but a tense standoff fueled by ideological differences – capitalism versus communism – and a global competition for influence.
> 
> Key elements included: mutual suspicion, an arms race (particularly nuclear weapons), proxy wars (like Korea and Vietnam), propaganda, and espionage.  It dominated international relations and shaped global politics for decades, ultimately leading to the collapse of the Soviet Union.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* US vs USSR after WWII, no direct war, arms race/proxy wars

---

## Item 8  (summary)

**Task given to the model:**
> Summarise the following text in exactly two sentences: ...

**Source text:**
> A fire at the Brantley warehouse on Tuesday night destroyed about 2 million dollars worth of electronics. Firefighters from five stations took six hours to bring the blaze under control, and 18 nearby homes were evacuated as a precaution but residents returned the next morning. Investigators say the fire started near a charging area for forklift batteries, although the exact cause is still unknown. No one was injured, and the company says it will reopen a smaller site within a month. The warehouse, built in 2004, stood in an industrial park on the edge of town and stored televisions, laptops and phone accessories for several retailers. Smoke could be seen from 20 kilometres away, and the main road was closed for most of the night. Insurance assessors will visit the site later this week.

**Constraint (already verified OK):** {'sentences': 2}

**REQUIRED facts (each must be in the summary):**
- fire destroyed about 2 million dollars of electronics
- 18 homes evacuated, no one injured
- started near forklift battery charging area, cause unknown

**Candidate answer:**

> A fire at the Brantley warehouse destroyed approximately 2 million dollars worth of electronics and took six hours for firefighters to control. The fire started near a charging area for forklift batteries, and the warehouse was evacuated for 18 homes, but residents returned the next morning.

**Label:** PASS — *(Claude draft, D10 rule; checked with Kabir)* core present (fire destroyed ~$2M of electronics; started near forklift chargers, 18 homes evacuated); nothing wrong. 'No injuries/cause unknown' are secondary. Kabir's call

---

## Item 9  (factual)

**Question:**
> Why do central banks raise interest rates to fight inflation, and what is the main trade-off?

**Reference answer:** Higher rates make borrowing more expensive, which reduces spending and investment and so cools demand and price growth; the trade-off is slower economic growth and possibly higher unemployment.

**REQUIRED points:**
- higher borrowing cost reduces demand
- lowers inflation pressure
- cost: slower growth / higher unemployment

**Candidate answer:**

> Central banks raise interest rates to curb inflation by making borrowing more expensive, which reduces spending and slows economic growth. The main trade-off is that higher rates can slow employment and growth, potentially leading to recession.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* costlier borrowing cuts spending, curbs inflation; trade-off slower growth/jobs

---

## Item 10  (summary)

**Task given to the model:**
> A report on remote work surveyed 5,000 employees at 120 companies. Workers who spent three days a week at home reported 12 percent higher job satisfaction than those who were fully in the office, and  ...

**Source text:**
> A report on remote work surveyed 5,000 employees at 120 companies. Workers who spent three days a week at home reported 12 percent higher job satisfaction than those who were fully in the office, and their managers rated their productivity as unchanged. However, junior staff who worked remotely more than four days a week were 20 percent less likely to be promoted within two years, which the authors attribute to fewer chances to be noticed and mentored. The report recommends hybrid schedules with scheduled in-person days for new hires. The survey was run by an independent research firm in 2023 and covered workers in finance, technology and healthcare administration. Average commuting time saved was 54 minutes a day. The authors noted that results may differ in jobs where workers must be present, and that only 8 percent of respondents were in management.

**Constraint (already verified OK):** {'bullets': 3}

**REQUIRED facts (each must be in the summary):**
- three remote days a week raised satisfaction by 12 percent with unchanged productivity
- juniors working remotely over four days were 20 percent less likely to be promoted
- recommends hybrid schedules with in-person days for new hires

**Candidate answer:**

> - The survey found that remote workers who spent three days a week at home reported 12 percent higher job satisfaction and unchanged productivity.  
> - Junior staff working remotely more than four days a week were 20 percent less likely to be promoted, attributed to fewer opportunities for recognition and mentorship.  
> - The report recommends hybrid schedules with scheduled in-person days for new hires, based on the survey's findings.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* all three required facts present and accurate

---

## Item 11  (factual)

**Question:**
> What was the Cold War?

**Reference answer:** The Cold War was a period of geopolitical rivalry between the United States and the Soviet Union and their allies after World War II, fought through an arms race and proxy conflicts rather than direct war, ending around 1991.

**REQUIRED points:**
- US vs Soviet Union rivalry after WWII
- no direct full-scale war (arms race, proxy wars)

**OPTIONAL points:**
- ended around 1991

**Candidate answer:**

> The Cold War was a period of geopolitical tension between the United States and the Soviet Union from 1947 to 1991. It involved ideological rivalry, military buildup, and proxy wars, but no direct military conflict. Key events include the Truman Doctrine, the Berlin Blockade, and the Cuban Missile Crisis. It shaped global politics and led to the formation of organizations like the United Nations and the NATO.

**Label:** FAIL — *(Claude draft, to be checked by Kabir)* wrong claim: says the Cold War led to the formation of the United Nations (UN was founded in 1945, before it)

---

## Item 12  (summary)

**Task given to the model:**
> When the Aral Sea began to shrink in the 1960s, the Soviet Union was diverting the rivers that fed it to irrigate cotton fields in Uzbekistan and Kazakhstan. By 2007 the sea had lost about 90 percent  ...

**Source text:**
> When the Aral Sea began to shrink in the 1960s, the Soviet Union was diverting the rivers that fed it to irrigate cotton fields in Uzbekistan and Kazakhstan. By 2007 the sea had lost about 90 percent of its volume, leaving ships stranded on dry sand, ending a fishing industry that once employed 40,000 people, and exposing toxic dust that harmed nearby residents. A dam completed in 2005 helped the northern part recover, with fish catches rising again, but the southern part is expected to remain largely dry. The Aral Sea was once the fourth-largest lake in the world. The rivers that fed it, the Amu Darya and the Syr Darya, still supply irrigation for cotton, which is a very thirsty crop. Governments in the region have planted salt-tolerant shrubs on the exposed seabed to reduce dust storms.

**Constraint (already verified OK):** {'bullets': 3}

**REQUIRED facts (each must be in the summary):**
- rivers diverted for cotton irrigation shrank the Aral Sea by about 90 percent
- fishing industry of 40,000 jobs ended and toxic dust spread
- 2005 dam helped the northern part recover, the southern part stays dry

**Candidate answer:**

> -   The Aral Sea shrunk significantly in the 1960s due to Soviet irrigation projects.
> -   By 2007, the sea lost 90% of its volume, causing economic hardship and environmental damage.
> -   A dam in 2005 partially recovered fish populations, but the southern part remains dry.

**Label:** PASS — *(Claude draft, D10 rule; checked with Kabir)* core present (river diversion shrank the sea ~90%; 2005 dam revived the north, south stays dry); consequences only vague but not wrong

---

## Item 13  (summary)

**Task given to the model:**
> A report on remote work surveyed 5,000 employees at 120 companies. Workers who spent three days a week at home reported 12 percent higher job satisfaction than those who were fully in the office, and  ...

**Source text:**
> A report on remote work surveyed 5,000 employees at 120 companies. Workers who spent three days a week at home reported 12 percent higher job satisfaction than those who were fully in the office, and their managers rated their productivity as unchanged. However, junior staff who worked remotely more than four days a week were 20 percent less likely to be promoted within two years, which the authors attribute to fewer chances to be noticed and mentored. The report recommends hybrid schedules with scheduled in-person days for new hires. The survey was run by an independent research firm in 2023 and covered workers in finance, technology and healthcare administration. Average commuting time saved was 54 minutes a day. The authors noted that results may differ in jobs where workers must be present, and that only 8 percent of respondents were in management.

**Constraint (already verified OK):** {'bullets': 3}

**REQUIRED facts (each must be in the summary):**
- three remote days a week raised satisfaction by 12 percent with unchanged productivity
- juniors working remotely over four days were 20 percent less likely to be promoted
- recommends hybrid schedules with in-person days for new hires

**Candidate answer:**

> -   A survey of 5,000 employees across 120 companies found that remote workers reported higher job satisfaction.
> -   Remote workers were less likely to be promoted within two years, likely due to reduced visibility.
> -   The report recommends hybrid schedules for new hires to improve opportunities for recognition and mentorship.

**Label:** PASS — *(Claude draft, D10 rule; checked with Kabir)* core present (hybrid raises satisfaction; heavy remote work hurts promotion; hybrid recommended). Drops the 'juniors, 4+ days' qualifier: tolerated under D10. Kabir's call

---

## Item 14  (factual)

**Question:**
> When and how did the Western Roman Empire end?

**Reference answer:** It is traditionally dated to 476 CE, when the Germanic general Odoacer deposed the last western emperor, Romulus Augustulus, after a long decline; the Eastern (Byzantine) Empire continued until 1453.

**REQUIRED points:**
- traditional date 476 CE
- Odoacer deposed Romulus Augustulus

**OPTIONAL points:**
- Eastern Empire survived until 1453

**Candidate answer:**

> The Western Roman Empire officially ended in 476 AD with the deposition of Romulus Augustulus by the Germanic chieftain Odoacer. 
> 
> It wasn’t a single event, but a gradual decline driven by a combination of factors:
> 
> *   **Internal Weakness:** Political instability, economic woes, and corruption weakened the empire.
> *   **Barbarian Invasions:** Waves of Germanic tribes, like the Visigoths, Vandals, and Ostrogoths, migrated into Roman territory, draining resources and military strength.
> *   **Economic Decline:** Trade routes diminished, and the empire struggled to maintain its vast infrastructure.
> 
> Ultimately, the Western Empire fractured, leading to the establishment of numerous kingdoms.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* 476, Odoacer deposed Romulus Augustulus; extra causes are accurate

---

## Item 15  (factual)

**Question:**
> What is a race condition in programming?

**Reference answer:** A race condition occurs when the result of a program depends on the unpredictable timing of concurrent operations on shared data, causing inconsistent or incorrect results; it is prevented with synchronisation such as locks or atomic operations.

**REQUIRED points:**
- outcome depends on timing of concurrent operations
- shared mutable state

**OPTIONAL points:**
- prevented by locks/atomics/synchronisation

**Candidate answer:**

> A race condition occurs when multiple threads or processes try to access and modify shared data simultaneously, leading to unpredictable and potentially incorrect results.  Essentially, the program’s execution is stalled while waiting for a resource to become available.
> 
> Imagine two threads trying to update the same variable in a shared memory location. One thread might read the value, modify it, and then write it back. The other thread reads the same value, modifies it independently, and writes it back. The final result depends on the order in which they both write, potentially leading to data corruption or incorrect calculations.
> 
> It’s a common source of bugs and security vulnerabilities.

**Label:** FAIL — *(Claude draft, to be checked by Kabir)* core definition right, but adds a wrong claim: 'execution is stalled while waiting for a resource' (that describes blocking/deadlock). Borderline

---

## Item 16  (factual)

**Question:**
> What does the Heisenberg uncertainty principle say?

**Reference answer:** It says that certain pairs of properties, such as position and momentum, cannot both be known with arbitrary precision at the same time; this is a fundamental feature of quantum systems, not just a limit of measuring instruments.

**REQUIRED points:**
- position and momentum can't both be exactly known

**OPTIONAL points:**
- fundamental to quantum mechanics, not instrument clumsiness

**Candidate answer:**

> The Heisenberg uncertainty principle states that certain physical properties, such as position and momentum, cannot be simultaneously measured with arbitrary precision. The more precisely one property is known, the less precisely the other can be determined. It reflects the inherent limitations in the precision of measurements in quantum mechanics.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* position and momentum can't both be known precisely; nothing wrong

---

## Item 17  (factual)

**Question:**
> What is the greenhouse effect?

**Reference answer:** The greenhouse effect is the warming that occurs when gases such as carbon dioxide and water vapour trap heat radiated from Earth's surface; human emissions of these gases strengthen it.

**REQUIRED points:**
- gases trap heat radiated by Earth
- keeps the planet warm

**OPTIONAL points:**
- increased by human greenhouse-gas emissions

**Candidate answer:**

> The greenhouse effect is a natural process vital for life on Earth. It occurs when certain gases in the atmosphere, like carbon dioxide, methane, and water vapor, trap heat from the sun. 
> 
> These gases allow sunlight to pass through, but they absorb and re-emit some of it back towards Earth, warming the planet. Without this effect, Earth would be a frozen wasteland.
> 
> However, human activities, primarily burning fossil fuels, are increasing these greenhouse gases, intensifying the effect and leading to global warming and climate change.

**Label:** PASS — *(Claude draft, D10 rule; checked with Kabir)* standard popular-science simplification ('trap the sun's heat'); rest accurate incl. human emissions (D10 clarification). Kabir's call

---

## Item 18  (summary)

**Task given to the model:**
> Summarise the following text as exactly 3 bullet points (each line starting with '- '): ...

**Source text:**
> Wildlife officials counted 3,200 snow leopards across Central Asia in a five-year survey, up from an estimate of 2,500 a decade ago. Conservationists credit community programmes that pay herders compensation for livestock lost to leopards, which has reduced revenge killings by about half in surveyed valleys. However, the survey used camera traps in only 40 percent of the range, and some experts believe the apparent rise may partly reflect better counting methods rather than a real increase. Climate change is shrinking the high-altitude habitat the animals depend on. Snow leopards live in 12 countries at altitudes up to 5,500 metres and are very hard to spot, which is why researchers rely on camera traps and droppings. They are listed as vulnerable. The survey was coordinated by a conservation coalition and took five years, covering about 1.2 million square kilometres.

**Constraint (already verified OK):** {'bullets': 3}

**REQUIRED facts (each must be in the summary):**
- 3,200 snow leopards counted, up from 2,500
- herder compensation halved revenge killings
- counting may overstate the rise; climate change shrinks habitat

**Candidate answer:**

> *   Snow leopard populations increased significantly in Central Asia over five years.
> *   Community compensation programs for livestock losses have reduced revenge killings.
> *   Camera trap use was limited to 40% of the range, raising questions about the true increase in snow leopards.

**Label:** PASS — *(Claude draft, D10 rule; checked with Kabir)* core present (count rose; rise may partly reflect better counting); numbers secondary; nothing wrong

---

## Item 19  (factual)

**Question:**
> Why is the sky blue?

**Reference answer:** Air molecules scatter short (blue) wavelengths of sunlight much more strongly than long (red) ones, a process called Rayleigh scattering, so blue light reaches our eyes from all directions.

**REQUIRED points:**
- Rayleigh scattering by air molecules
- shorter/blue wavelengths scatter more

**Candidate answer:**

> The sky appears blue due to Rayleigh scattering, a phenomenon where shorter wavelengths of light (blue and violet) are scattered more efficiently by the atmosphere than longer wavelengths. This scattering is more pronounced for blue light, which is why the sky appears blue during the day.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* Rayleigh scattering, shorter wavelengths scatter more

---

## Item 20  (summary)

**Task given to the model:**
> Condense this passage in exactly one sentence. Keep only facts stated in the text. ...

**Source text:**
> A software update released on Tuesday fixes a security flaw that could let attackers read messages sent through the Chatly app. The flaw, found by an independent researcher, affected versions released since September and was present on both phones and computers. Chatly says it has seen no evidence that the weakness was used. Users should install version 5.3 as soon as possible; the update downloads automatically if automatic updates are switched on. Chatly has 40 million monthly users in 90 countries and is known for its group chats and disappearing messages. The security researcher who found the flaw was paid a reward of 15,000 dollars under the company's bug-bounty programme. Chatly said it will publish a full technical explanation in two weeks.

**Constraint (already verified OK):** {'sentences': 1}

**REQUIRED facts (each must be in the summary):**
- update fixes a security flaw in Chatly
- install version 5.3
- no evidence the flaw was exploited

**Candidate answer:**

> A software update released on Tuesday fixes a security flaw that could allow attackers to read messages sent through the Chatly app, found by an independent researcher, affecting versions released since September and present on both phones and computers, with Chatly stating no evidence of the flaw being exploited, and users are advised to install version 5.3 as soon as possible, with the update downloading automatically if automatic updates are enabled, and the company will publish a full technical explanation in two weeks.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* all three required facts present (length is checked by code, not here)

---

## Item 21  (factual)

**Question:**
> Why does the Moon have phases?

**Reference answer:** The Moon orbits Earth, so from Earth we see different portions of its sunlit half over the month; the phases are not caused by Earth's shadow.

**REQUIRED points:**
- we see different parts of the sunlit half as it orbits

**OPTIONAL points:**
- not caused by Earth's shadow

**Candidate answer:**

> The Moon’s phases are caused by the changing angles at which we see the sunlit portion of the Moon as it orbits Earth.
> 
> Here’s the breakdown:
> 
> * **New Moon:** The Moon is between the Earth and the Sun, so the side facing us is not illuminated.
> * **Waxing Crescent:** A sliver of light appears.
> * **First Quarter:** Half of the Moon is illuminated.
> * **Waxing Gibbous:** More than half is illuminated.
> * **Full Moon:** The Earth is between the Sun and Moon, so the entire face is illuminated.
> * **Waning Gibbous:** More than half is illuminated, but the illuminated portion starts to decrease.
> * **Third Quarter:** Half of the Moon is illuminated again.
> * **Waning Crescent:** The illuminated portion decreases again.
> 
> It’s a continuous cycle of phases as the Moon orbits.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* sees different parts of the sunlit side as the Moon orbits

---

## Item 22  (factual)

**Question:**
> Why does the Moon have phases?

**Reference answer:** The Moon orbits Earth, so from Earth we see different portions of its sunlit half over the month; the phases are not caused by Earth's shadow.

**REQUIRED points:**
- we see different parts of the sunlit half as it orbits

**OPTIONAL points:**
- not caused by Earth's shadow

**Candidate answer:**

> The Moon has phases due to its orbit around Earth and the relative positions of the Moon, Earth, and Sun. As the Moon orbits Earth, different portions of its illuminated side face Earth, creating the cycle of phases. This happens because the Moon is not a perfect sphere and its shadow shifts over time.

**Label:** FAIL — *(Claude draft, to be checked by Kabir)* wrong claim: phases happen 'because the Moon is not a perfect sphere and its shadow shifts'

---

## Item 23  (factual)

**Question:**
> What is a bond in finance?

**Reference answer:** A bond is a loan to a government or company: the issuer pays the holder regular interest (the coupon) and repays the face value at maturity.

**REQUIRED points:**
- a loan made by the investor
- pays interest/coupon
- principal returned at maturity

**Candidate answer:**

> A bond is a debt security issued by a government or corporation to raise capital. When an investor buys a bond, they lend money to the issuer in return for periodic interest payments and the eventual repayment of the principal. Bonds are a common method of raising funds for governments, corporations, and other entities.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* loan to issuer, periodic interest, principal repaid

---

## Item 24  (factual)

**Question:**
> How do vaccines work?

**Reference answer:** Vaccines expose the immune system to a harmless form or piece of a pathogen so it learns to recognise it and creates memory cells, allowing a faster, stronger response if the real pathogen appears.

**REQUIRED points:**
- introduce a harmless antigen or part of a pathogen
- immune system builds memory

**OPTIONAL points:**
- faster response on later exposure

**Candidate answer:**

> Vaccines work by training the immune system to recognize harmful pathogens, such as viruses or bacteria. When a person is exposed to a harmless version of a pathogen (like a virus), their immune system produces antibodies and memory cells. If they encounter the actual pathogen later, their immune system quickly responds by producing antibodies and activating immune cells to fight the infection. This provides protection without causing the disease.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* harmless version of the pathogen, antibodies and memory cells

---

## Item 25  (summary)

**Task given to the model:**
> When the Aral Sea began to shrink in the 1960s, the Soviet Union was diverting the rivers that fed it to irrigate cotton fields in Uzbekistan and Kazakhstan. By 2007 the sea had lost about 90 percent  ...

**Source text:**
> When the Aral Sea began to shrink in the 1960s, the Soviet Union was diverting the rivers that fed it to irrigate cotton fields in Uzbekistan and Kazakhstan. By 2007 the sea had lost about 90 percent of its volume, leaving ships stranded on dry sand, ending a fishing industry that once employed 40,000 people, and exposing toxic dust that harmed nearby residents. A dam completed in 2005 helped the northern part recover, with fish catches rising again, but the southern part is expected to remain largely dry. The Aral Sea was once the fourth-largest lake in the world. The rivers that fed it, the Amu Darya and the Syr Darya, still supply irrigation for cotton, which is a very thirsty crop. Governments in the region have planted salt-tolerant shrubs on the exposed seabed to reduce dust storms.

**Constraint (already verified OK):** {'bullets': 3}

**REQUIRED facts (each must be in the summary):**
- rivers diverted for cotton irrigation shrank the Aral Sea by about 90 percent
- fishing industry of 40,000 jobs ended and toxic dust spread
- 2005 dam helped the northern part recover, the southern part stays dry

**Candidate answer:**

> - The Aral Sea shrank in the 1960s due to Soviet diversion of rivers for cotton irrigation.  
> - The sea lost 90% of its volume, causing ecological and health issues in the region.  
> - Salt-tolerant shrubs were planted to combat dust storms and aid recovery in the northern part.

**Label:** FAIL — *(Claude draft, to be checked by Kabir)* misses 40,000 jobs/toxic dust and the 2005 dam; credits the shrubs with the northern recovery (the dam did it) — wrong

---

## Item 26  (factual)

**Question:**
> What does the Heisenberg uncertainty principle say?

**Reference answer:** It says that certain pairs of properties, such as position and momentum, cannot both be known with arbitrary precision at the same time; this is a fundamental feature of quantum systems, not just a limit of measuring instruments.

**REQUIRED points:**
- position and momentum can't both be exactly known

**OPTIONAL points:**
- fundamental to quantum mechanics, not instrument clumsiness

**Candidate answer:**

> The Heisenberg uncertainty principle states that it’s impossible to simultaneously know with perfect accuracy both the position and momentum of a particle.  In simpler terms, the more precisely you know one, the less precisely you know the other.
> 
> Mathematically, it’s expressed as Δx Δp ≥ ħ/2, where Δx is the uncertainty in position, Δp is the uncertainty in momentum, and ħ is the reduced Planck constant.
> 
> This isn’t about limitations in our measuring instruments; it’s a fundamental property of quantum mechanics. It implies that the act of observing a particle inevitably disturbs it, altering its properties.

**Label:** FAIL — *(Claude draft, to be checked by Kabir)* correct statement plus the formula, but ends with 'observing a particle inevitably disturbs it', the observer-effect misconception. Borderline

---

## Item 27  (summary)

**Task given to the model:**
> The government has announced a plan to give 1.2 million households a one-off payment of 150 pounds towards winter heating bills. The payment will be made automatically in November to people receiving  ...

**Source text:**
> The government has announced a plan to give 1.2 million households a one-off payment of 150 pounds towards winter heating bills. The payment will be made automatically in November to people receiving certain benefits, and the 180 million pound cost will come from existing budgets. Charities welcomed the move but said it is smaller than last year's help and does not reach many pensioners on low incomes. Last year's payment was 300 pounds and reached 2.4 million households, which is why charities say this year's scheme is less generous. Energy prices have fallen 22 percent since the peak, but remain well above levels from before 2021. The finance minister said the government would keep the policy under review.

**Constraint (already verified OK):** {'max_words': 35}

**REQUIRED facts (each must be in the summary):**
- 150 pound one-off payment to 1.2 million households
- paid in November, 180 million pounds
- charities say it is smaller and misses some pensioners

**Candidate answer:**

> Government offers 1.2 million households 150镑 winter payment, costing 180 million pounds, with charities criticizing it as smaller than last year's aid and not reaching many pensioners.

**Label:** PASS — *(Claude draft, D10 rule; checked with Kabir)* content: core present (150-pound payment to 1.2m households; charities say smaller, misses pensioners). NOTE: final score FAILS via the language check (stray '镑')

---

## Item 28  (summary)

**Task given to the model:**
> A local charity, Warm Winter, collected 8,400 coats during its autumn drive, double the number from last year. Volunteers cleaned and sorted the coats and will give them out at six community centres f ...

**Source text:**
> A local charity, Warm Winter, collected 8,400 coats during its autumn drive, double the number from last year. Volunteers cleaned and sorted the coats and will give them out at six community centres from 1 November. The charity says demand has risen because more families are struggling with heating costs. It still needs volunteers on Saturdays and has set up a hotline for people who cannot reach the centres. Last year the drive collected 4,200 coats and had to turn people away at two centres because supplies ran out. This year a clothing retailer donated 1,500 new coats, and a transport company is delivering them for free. Volunteers meet at the warehouse at 9 am, and training is provided on the first day.

**Constraint (already verified OK):** {'max_words': 35}

**REQUIRED facts (each must be in the summary):**
- Warm Winter collected 8,400 coats, double last year
- distributed at six community centres from 1 November
- needs Saturday volunteers

**Candidate answer:**

> Warm Winter collected 8,400 coats, doubling last year’s, and demand increased due to heating costs. They’ll distribute them at community centres, and a hotline is available for those unable to reach them.

**Label:** PASS — *(Claude draft, D10 rule; checked with Kabir)* core present (8,400 coats, double last year, handed out at community centres); date/Saturday volunteers secondary. Kabir's call

---

## Item 29  (factual)

**Question:**
> What is a CPU cache and why does it exist?

**Reference answer:** A CPU cache is a small, very fast memory close to the processor that stores recently or frequently used data so the CPU does not have to wait for the much slower main memory.

**REQUIRED points:**
- small fast memory near the CPU
- stores frequently/recently used data
- reduces slow main-memory accesses

**Candidate answer:**

> A CPU cache is a small, fast memory located within the CPU itself. It stores frequently accessed data and instructions, allowing the CPU to access them much quicker than retrieving them from slower RAM.
> 
> Its existence stems from two key reasons: **speed** and **efficiency**.  RAM is slower than the CPU, and caching reduces the number of trips the CPU needs to make to access data, significantly boosting overall performance.  It also helps to mitigate the effects of memory bottlenecks, improving the overall responsiveness of the system.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* small fast memory, frequently used data, fewer slow RAM trips

---

## Item 30  (summary)

**Task given to the model:**
> Summarise the following text in exactly one sentence: ...

**Source text:**
> Coastal Airways will start a direct flight between Lisbon and Cape Town in October, the first non-stop service between the two cities. The flights will run three times a week on a 220-seat aircraft and take about 11 hours. Introductory fares begin at 389 euros one way. The airline says the route responds to growing demand from tourists and from Portuguese families with ties to southern Africa. Currently passengers between the two cities must change planes in Johannesburg or Dubai, which can add five hours to the trip. Coastal Airways, founded in 2011, flies to 24 destinations and operates a fleet of 18 aircraft. Bookings open on 1 July, and the airline will offer extra baggage on the first week of flights.

**Constraint (already verified OK):** {'sentences': 1}

**REQUIRED facts (each must be in the summary):**
- new non-stop Lisbon-Cape Town flight from October
- three flights a week, about 11 hours
- fares from 389 euros

**Candidate answer:**

> Coastal Airways will launch a direct flight between Lisbon and Cape Town in October, offering three weekly non-stop services on a 220-seat aircraft with fares starting at 389 euros, to meet growing demand from tourists and Portuguese families with ties to southern Africa, replacing the longer and more complex route through Johannesburg or Dubai.

**Label:** PASS — *(Claude draft, D10 rule; checked with Kabir)* core present (new non-stop Lisbon–Cape Town from October, 3×/week, from 389 euros); '11 hours' secondary

---

## Item 31  (summary)

**Task given to the model:**
> Condense this passage in exactly one sentence. Keep only facts stated in the text. ...

**Source text:**
> The Silk Road was not a single road but a network of trade routes linking China with the Mediterranean from about the second century BCE. Merchants rarely travelled the whole distance; goods such as silk, spices and paper passed through many hands. The network also carried ideas and religions, including Buddhism, and diseases such as the plague. It declined as sea routes became cheaper and as the Ottoman Empire controlled key territories in the fifteenth century. Samarkand and Kashgar were among the best-known stopping points, where caravans rested and traded. Camels and horses were the main means of transport across the deserts and mountains. The name 'Silk Road' was only coined in 1877 by a German geographer, long after the routes had fallen into decline.

**Constraint (already verified OK):** {'sentences': 1}

**REQUIRED facts (each must be in the summary):**
- network of trade routes linking China and the Mediterranean
- carried goods, ideas and diseases
- declined as sea routes grew cheaper / Ottoman control

**Candidate answer:**

> The Silk Road was a network of trade routes linking China with the Mediterranean, carried by merchants and including goods, ideas, and religions like Buddhism, which declined due to cheaper sea routes and Ottoman Empire control in the fifteenth century.

**Label:** PASS — *(Claude draft, D10 rule; checked with Kabir)* core present (network linking China–Mediterranean carrying goods and ideas; declined with sea routes/Ottomans); 'diseases' secondary. Kabir's call

---

## Item 32  (factual)

**Question:**
> What was the Industrial Revolution?

**Reference answer:** The Industrial Revolution was the shift from hand production to machine and factory production that began in Britain in the late 1700s, driven by steam power and mechanised textiles, and it led to rapid urbanisation.

**REQUIRED points:**
- began in Britain in the late 18th century
- machines, factories and steam power

**OPTIONAL points:**
- urbanisation / social change

**Candidate answer:**

> The Industrial Revolution was a period of major technological advancements beginning in the late 18th and early 19th centuries, primarily in Britain, that fundamentally transformed economies and societies. It involved a shift from hand-crafted production to machine-powered manufacturing. 
> 
> Key changes included the invention of new machines like the steam engine and power loom, leading to increased production, urbanization, and the growth of factories. It spurred new industries, like textiles and iron, and dramatically altered social structures, creating new classes and impacting daily life.  It’s a pivotal moment in history driving global change.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* Britain, late 18th century, machines, factories, steam

---

## Item 33  (summary)

**Task given to the model:**
> Condense this passage in no more than 25 words. Keep only facts stated in the text. ...

**Source text:**
> A 400-year-old oak tree in the Weald Forest was cut down illegally last week, and police are investigating. The tree, known locally as the Old Warden, was thought to have sheltered soldiers in the English Civil War and was a popular walking destination. The forest trust has offered a 10,000 pound reward for information and says the trunk, about 3 metres around, was removed with a chainsaw at night. The trust will plant a sapling grown from one of the tree's acorns on the same spot. The Weald Forest covers 1,400 hectares and receives about 300,000 visitors a year. Rangers found the stump and sawdust on Monday morning and think the work took several hours. It is a criminal offence to fell a protected tree, punishable with a fine of up to 20,000 pounds, and local woodworkers have been told to report any large oak timber offered for sale.

**Constraint (already verified OK):** {'max_words': 25}

**REQUIRED facts (each must be in the summary):**
- 400-year-old oak 'Old Warden' illegally cut down
- 10,000 pound reward offered
- sapling from its acorns will be planted

**Candidate answer:**

> A 400-year-old oak tree in the Weald Forest was illegally felled, and a reward of £10,000 is offered.

**Label:** PASS — *(Claude draft, D10 rule; checked with Kabir)* core present (400-year-old oak illegally felled; 10,000-pound reward); sapling secondary

---

## Item 34  (factual)

**Question:**
> What is inflation?

**Reference answer:** Inflation is a sustained rise in the general level of prices, which reduces the purchasing power of money.

**REQUIRED points:**
- general/sustained rise in prices
- purchasing power of money falls

**Candidate answer:**

> Inflation is a sustained increase in the general price level of goods and services in an economy over a period of time. Essentially, it means your money buys less than it used to.
> 
> It’s driven by increased demand, supply chain issues, or government policies that lead to higher production costs.  
> 
> While a small amount of inflation can be healthy, high inflation erodes purchasing power and can destabilize an economy.  Central banks typically use monetary policy to manage inflation through adjustments to interest rates and money supply.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* sustained rise in general prices, money buys less

---

## Item 35  (factual)

**Question:**
> What is the difference between a recession and a depression?

**Reference answer:** A recession is a significant, widespread decline in economic activity, often defined as two consecutive quarters of falling GDP; a depression is a far more severe and prolonged downturn, such as the 1930s Great Depression, and has no single official definition.

**REQUIRED points:**
- recession: shorter/milder decline (often two quarters of falling GDP)
- depression: much more severe and prolonged

**OPTIONAL points:**
- depression has no formal precise definition

**Candidate answer:**

> A recession is a temporary decline in economic activity, while a depression is a more severe and prolonged downturn. Recession involves a decline in GDP, employment, and consumer spending, but recovery is possible. A depression lasts longer and causes deeper economic damage, often leading to prolonged unemployment and structural changes in the economy.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* recession = temporary decline, depression = more severe and prolonged

---

## Item 36  (factual)

**Question:**
> What is inflation?

**Reference answer:** Inflation is a sustained rise in the general level of prices, which reduces the purchasing power of money.

**REQUIRED points:**
- general/sustained rise in prices
- purchasing power of money falls

**Candidate answer:**

> Inflation is a rise in the general price level of goods and services over time. It reduces purchasing power and is typically caused by an increase in demand or a decrease in supply. It is a key economic indicator and can affect employment, interest rates, and overall economic growth.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* general price rise, reduces purchasing power

---

## Item 37  (summary)

**Task given to the model:**
> Summarise the following text in no more than 25 words: ...

**Source text:**
> The Ferris Valley railway, closed in 1966, will partly reopen next year after a campaign by local residents raised 2.5 million pounds. Only 9 of the original 24 kilometres will carry trains at first, run by volunteers using restored steam locomotives at weekends. A further 4 million pounds is needed to rebuild a collapsed bridge before the full line can reopen. Organisers expect the heritage line to bring 60,000 tourists a year to the valley. The Ferris Valley line was closed in 1966 as part of national cuts to rural railways, and its tracks lay overgrown for 30 years before volunteers began clearing them. The reopened stretch will have two stations and a small museum. The campaign group, founded in 2008, has about 1,200 members and receives no government funding.

**Constraint (already verified OK):** {'max_words': 25}

**REQUIRED facts (each must be in the summary):**
- railway closed in 1966 partly reopens next year
- only 9 of the 24 km will carry trains
- 4 million more needed for the bridge

**Candidate answer:**

> The Ferris Valley railway will partially reopen after a £2.5 million campaign, with volunteers restoring tracks and rebuilding a bridge, attracting 60,000 tourists annually.

**Label:** FAIL — *(Claude draft, to be checked by Kabir)* misses 1966, '9 of 24 km' and '4 million more for the bridge'; says volunteers are rebuilding the bridge (text: money still needed) — wrong

---

## Item 38  (summary)

**Task given to the model:**
> Condense this passage in exactly one sentence. Keep only facts stated in the text. ...

**Source text:**
> The company Nuvo Foods has recalled 120,000 jars of peanut sauce after tests found traces of an allergen that was not listed on the label. The affected jars carry batch numbers beginning with 24B and were sold in 11 countries between January and April. No illnesses have been confirmed. Customers are asked to stop using the product and can return it to the store for a full refund. Nuvo Foods, based in Rotterdam, sells its sauces in more than 30 countries and employs 2,800 people. The company discovered the problem during routine checks after a customer in Germany reported a mild reaction, which was later found to be unrelated. A hotline and a web page with photos of the batch codes have been set up.

**Constraint (already verified OK):** {'sentences': 1}

**REQUIRED facts (each must be in the summary):**
- recall of 120,000 jars of peanut sauce
- unlisted allergen found
- full refund available

**Candidate answer:**

> Nuvo Foods recalled 120,000 jars of peanut sauce with batch numbers starting with 24B, sold in 11 countries between January and April, after testing found an unlisted allergen, with no confirmed illnesses, and provided a refund option, while the company discovered the issue during routine checks following a customer's mild reaction.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* 120,000 jars, unlisted allergen, refund; extra details accurate

---

## Item 39  (summary)

**Task given to the model:**
> Condense this passage in exactly one sentence. Keep only facts stated in the text. ...

**Source text:**
> The Silk Road was not a single road but a network of trade routes linking China with the Mediterranean from about the second century BCE. Merchants rarely travelled the whole distance; goods such as silk, spices and paper passed through many hands. The network also carried ideas and religions, including Buddhism, and diseases such as the plague. It declined as sea routes became cheaper and as the Ottoman Empire controlled key territories in the fifteenth century. Samarkand and Kashgar were among the best-known stopping points, where caravans rested and traded. Camels and horses were the main means of transport across the deserts and mountains. The name 'Silk Road' was only coined in 1877 by a German geographer, long after the routes had fallen into decline.

**Constraint (already verified OK):** {'sentences': 1}

**REQUIRED facts (each must be in the summary):**
- network of trade routes linking China and the Mediterranean
- carried goods, ideas and diseases
- declined as sea routes grew cheaper / Ottoman control

**Candidate answer:**

> The Silk Road was a network of trade routes linking China with the Mediterranean from about the second century BCE, carrying goods like silk and paper, ideas, religions, and diseases, and declining due to cheaper sea routes and Ottoman control, with Samarkand and Kashgar being key stopping points and camels and horses being the main transport means.

**Label:** PASS — *(Claude draft, to be checked by Kabir)* all three required facts present and accurate

---

## Item 40  (summary)

**Task given to the model:**
> Condense this passage as exactly 3 bullet points (each line starting with '- '). Keep only facts stated in the text. ...

**Source text:**
> A trial of a new migraine drug involved 1,800 patients across 14 countries. Participants who took the drug monthly had on average 4.2 fewer migraine days per month, compared with 1.9 fewer days for those on a placebo. The most common side effects were mild nausea and fatigue, reported by 7 percent of patients. Researchers stressed that the study lasted only six months and excluded people over 65, so long-term safety and effects in older adults remain unknown. The manufacturer will apply for approval next year. Migraine affects about one in seven people worldwide and is more common in women. The drug works by blocking a protein called CGRP, which is involved in pain signalling. The trial was funded by the manufacturer, but the analysis was conducted by an independent university group and published in a medical journal.

**Constraint (already verified OK):** {'bullets': 3}

**REQUIRED facts (each must be in the summary):**
- drug cut migraine days by 4.2 vs 1.9 for placebo
- side effects mild nausea/fatigue in 7 percent
- only six months and excluded over-65s; approval to be sought next year

**Candidate answer:**

> *   A trial involved 1,800 patients across 14 countries.
> *   Monthly users experienced an average 4.2 fewer migraine days.
> *   The most common side effects were mild nausea and fatigue.

**Label:** FAIL — *(Claude draft, D10 rule; checked with Kabir)* core missing: '4.2 fewer days' without the placebo's 1.9 overstates the effect; trial limits (6 months, no over-65s) missing
