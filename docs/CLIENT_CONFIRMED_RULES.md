# SeaTac AI Client Confirmed Calculation Rules

> Converted to Markdown from the team's Word document *SeaTac-AI-Client-Confirmed-Calculation-Rules.docx* (prepared October 15, 2026). Wording unchanged; page-break "continued" headings merged. Implementation status against these rules is tracked in [DB_SCHEMA.md](DB_SCHEMA.md).

Prepared October 15, 2026 from the client response shared with the project team. This is an organized summary of that response, not a record of completed implementation or testing.

## Confirmed metric definitions

### Q1 Taxi in by aircraft type

**Interval and grouping.** Use wheels-down, when the aircraft physically touches down, as the start and arrival at parking (in-block) as the end. Calculate each eligible flight’s elapsed time in minutes and average by aircraft type.

**Important restriction.** Do not substitute “actual landing” for wheels-down. Their equivalence has not been confirmed.

### Q2 Taxi out by hour

**Interval.** Use departure from parking (off-block) as the start and actual takeoff as the end.

**Grouping.** Group by the local hour the aircraft leaves parking. Keep complete dates and timestamps when flights cross midnight.

### Q3 Movement area occupancy

**Area.** Include the defined runway and taxiway movement area, described by the client as the hatched area. Exclude parking positions and locations outside that boundary.

**Intervals.** For arrivals, count from touchdown until exit from the defined area toward parking. For departures, count from entry into the defined area until takeoff.

**Counting.** Include the entry timestamp and exclude the exit timestamp. Show the highest number of aircraft simultaneously present during each hour. Account for exit and re-entry; never count the same aircraft twice at a given time.

### Q4 Runway occupancy

**Arrivals.** Measure from touchdown until the aircraft leaves the runway.

**Departures.** Measure from runway entry until takeoff. Use the 76-second entry-to-takeoff interval in the example discussed, not the 111-second entry-to-Clear-Active interval.

**Excluded term.** Clear Active is an internal term and must not be used for this project’s runway-occupancy definition.

### Q5 Takeoff delay

**Calculation.** Compare actual takeoff with scheduled takeoff and report the difference in minutes. Positive means late; negative means early. Do not substitute scheduled or predicted departure-from-parking time.

**Source and threshold.** The client identifies Aerobahn as usually the most accurate source. Apply no delay threshold in this version; classification exactly at a threshold therefore does not apply.

**Missing schedule.** If scheduled takeoff is unavailable, state that the calculation cannot be completed.

### Q6 Taxi times by weight class

**Method.** Show arrival and departure taxi averages separately using Q1 and Q2. Use the ICAO weight classification.

**Categories.** Keep unknown classifications in an “Unknown” group. Show “No data” when a category has no usable records.

### Q7 Taxiway usage

**Counting unit.** Count distinct flights using each recorded taxiway section. Count each flight once per section even if it passes through that section more than once.

**Time and names.** Use section-entry time to select the reporting period. Tango means T, Hotel means H, and Whiskey means W.

### Q8 Wheels down to parking

**Method.** Use the same touchdown-to-parking interval as Q1. Show one overall average across all eligible arrivals. Q1 provides the aircraft-type breakdown; Q8 summarizes all included arrivals.

### Q9 Runway activity

**Counting.** Count each verified takeoff and completed landing once by runway. Use actual takeoff for departures and wheels-down for arrivals. Report missed approaches separately because they are not completed landings.

**Window.** Include events exactly at the reporting-window start and exclude those exactly at its end.

**Airport scope.** Use verified airport and runway identifiers. The client stated: “Anything NOT (FAA) or (SWIM) is SEA local.” The response also states that the exact fields identifying SEA events still need confirmation; field mapping remains open.

### Q10 Historical peak hours

**Busy means.** The combined number of takeoffs and completed landings. Rank hours separately for each local day and show ties.

**Limits.** Keep simultaneous aircraft counts and taxi durations as separate measures. This is historical activity analysis, not a forecast.

## Confirmed selection rules

The client confirmed the proposed selection rules and instructed the team to use airport local time. The following restates those rules from the confirmation table with Q1 and Q8 updated to the confirmed wheels-down start.

**Q1 and Q8.** Select arrivals by wheels-down time.

**Q2.** Select departures by off-block time.

**Q3.** Include occupancy intervals overlapping the selected window.

**Q4.** Select operations by the start of their occupancy interval: touchdown for arrivals and runway entry for departures.

**Q5.** Select departures by actual takeoff time.

**Q6.** Use the corresponding Q1 or Q2 selection rule.

**Q7.** Select by taxiway-section entry time.

**Q9 and Q10.** Select takeoffs by actual takeoff and completed landings by wheels-down.

## Rules applying across metrics

### Time and reporting days

**Display.** Always display Seattle local time with daylight saving adjustments. Use midnight-to-midnight local reporting days and retain full dates across midnight.

**Boundaries.** Apply the confirmed start-inclusive, end-exclusive time-window convention.

### Flight identity and exclusions

**Identity.** Calculate once per identified flight instance, not once per call sign.

**Excluded averages.** Exclude records with missing endpoints, unresolved flight matches or negative elapsed durations from the affected averages. Report the exclusion reasons.

**Valid values.** Retain zero and unusually long valid durations. Negative takeoff delay is a valid early departure and must be retained.

### Precision and presentation

**Precision.** Use full timestamp precision for calculations. Display average minutes to two decimal places.

**Counts.** Show included and excluded counts and always show sample size. No minimum group size is required for this version.

**Empty groups.** Display “No data” when there are no eligible records; do not replace missing results with zero.

## Implementation details still requiring verification

The following are team implementation checks, not additional client-approved definitions. They do not reopen the confirmed business decisions above.

**SEA field mapping.** Identify the exact columns and values implementing the client’s non-FAA/non-SWIM guidance. Verify airport and runway identifiers before filtering.

**Area boundary.** Locate the referenced hatched-area definition and map entry/exit events to it, including re-entry.

**Timezone and missing sources.** Verify source timestamp storage and daylight saving handling. Do not assume a timezone or silently substitute another timestamp when a required field is missing.

**Source identifiers and taxiway codes.** Verify the flight-instance mapping and source section-code mapping. T/H/W meanings alone do not map every anonymized segment code to a named taxiway.

**Recalculation.** Recalculate earlier taxi-in references using wheels-down. Earlier results based on Actual Landing remain historical checks and are not automatically approved reference answers under Q1/Q8.
