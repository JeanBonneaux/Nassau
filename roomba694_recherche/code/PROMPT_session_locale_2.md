# Prompt pour la session Claude Code locale — suite après la recherche du 2026-11-10

À coller tel quel au démarrage d'une session Claude Code sur l'ordinateur relié au robot (clone local du dépôt JeanBonneaux/Nassau). Rédigé en anglais, comme la demande du 2026-11-10. Il remplace [PROMPT_session_locale.md](PROMPT_session_locale.md), qui couvrait le premier essai de la liaison série, terminé depuis.

---

# Roomba 694: pick up the sensor research and continue the plan on the real robot

I am the owner of this robot and a beginner in electronics. A cloud session reviewed my setup (a Roomba 694 driven by an ESP32, with a GY-521 gyroscope board and an HC-SR04 distance sensor on an SG90 servo) and wrote a report with a plan. It could not touch the robot: nothing in the report has been tried. Your job is to fetch that work and carry out the plan with me, step by step, on the real hardware connected to this computer.

## 1. Get the work

- Run `git status` first. If there are uncommitted changes or commits that were never pushed, show them to me and keep them (commit them) before switching branch.
- Then `git fetch origin`, `git checkout claude/pensive-hopper-qmvast`, `git pull`. This branch contains everything from the earlier working branch `claude/eager-ride-crj3f0` plus the research. If this computer has work on the old branch that was never pushed, merge it into the new branch and tell me if anything conflicts. From now on, work and push on `claude/pensive-hopper-qmvast`.

## 2. Read before proposing anything

In this order, all under `roomba694_recherche/`:

1. `reports/Roomba 694 sensor exploitation ideas.md`: the report. Its table of twelve problems, its quick wins, its five ideas to do first and its section "A suggested order of work" are the plan.
2. `code/README.md`: wiring, pin table, firmware features, build and update commands.
3. `notes/H_cartographie_strategie.md`: my goals and the earlier strategy.
4. `code/journal_wifi.md`, last sections: what was really tested, and the style of the journal you will continue.

The seven research notes in `research_notes/Roomba 694 sensor exploitation ideas/` hold the detail behind the report (about 630 kB). Do not read them all up front. Open the one that matches what we are working on: `firmware_wiring_audit.md` before any firmware change (findings with file and line), `recorded_data_analysis.md` and the scripts in `data_analysis/` for anything measured, then `roomba_builtin_sensors.md`, `sonar_single_ultrasonic.md`, `imu_mpu6050.md`, `esp32_radio_onchip.md` and `fusion_algorithms_prior_art.md` by topic.

How to treat the report: its accuracy figures are estimates and its pass or fail thresholds are first guesses. When a measurement on the robot contradicts it, the measurement wins; write the result down and say plainly which claim of the report it replaces. Its line numbers are those of firmware v5: re-read the code before editing, and check which firmware is actually running on the board before assuming anything.

## 3. The plan

Follow the report's order of work, one step at a time:

- Step 0, one evening with no new code: the multimeter and ruler checks, the first recording of the existing CSV log during a hand-driven drive and a spin, the paper-and-tape test under a floor sensor, the dock checks.
- Step 1, firmware foundations: the quick wins, one change at a time.
- Steps 2 to 7 as the report lists them: calibration session, a room from spins on the PC, sideways look and floor lines, dock and memory, first moves decided by the firmware, wall-following and stripes.

If I ask to skip ahead (for example to PC-only work that needs no robot), do it, and say what the skipped step would have settled.

Your first answer, after reading: a short summary of where the project stands, then the step 0 checklist split into what I do with my hands and what you do, and the list of what you need from me (multimeter, ruler, masking tape, white paper, a 10 kΩ resistor, which parts on order have arrived, how much time I have). Then wait for my go.

## 4. How to work with me

- Explain each step in plain words, one thing at a time. For anything physical, tell me exactly where the probe or the wire goes, using the labels printed on the board, and ask for a photo before I power up after a wiring change.
- Ask before installing anything, before any wiring change, and before anything that makes the robot move.
- Wiring changes are made with the board unpowered. Measure on the breadboard, never inside the robot's socket, where the battery pins sit next to the signal pins.
- Reply in the language I write to you in. The repository's documents, journals, code comments and commit messages are in French: keep them in French.

## 5. Safety rules

These stay in force unless I change them explicitly:

- Open Interface Safe mode only, never Full mode (opcode 132). 150 mm/s at most. Brushes and vacuum off.
- Robot on the floor, off its dock, in a clear space. Every session ends with `s` then `x`; otherwise the robot neither sleeps nor charges.
- A movement decided by the firmware and not by my finger (today only the spin in place) needs my yes each time, with short first runs. Safe mode does not stop the robot on a bump, so no forward or backward move decided by the firmware until the bumper stop exists in the firmware (problem 5 of the report).
- If the board loses power, the robot keeps its last wheel order, and I must lift it or press CLEAN. Long runs without my hand on the controls wait for the 5 V supply taken from the robot.
- Never connect the robot's pins 1 and 2 (battery voltage) except through the converter procedure of the README, and never the PC's USB together with another supply.
- Safe mode drops to Passive when a floor sensor sees a drop (dark surfaces can read as drops, so floor markers must be light, never black), when a wheel drops (door sills, dock ramp, lifting) and on a powered dock. After such a drop, do not put the robot back in Safe mode on your own: tell me.

## 6. Firmware changes

Small and one at a time. Each change is compiled, loaded, and checked with the robot standing still before any test in motion. Say what changed and bump the version shown by the firmware. Do not rework the structure or touch a safety interlock without telling me first. Build and update commands are in the README.

## 7. Record and push

- One new numbered section per session in `code/journal_wifi.md`, in French and in the style of the existing ones: what was done, raw outputs, results against the report's pass criteria, surprises.
- Recordings go in `mesures/` with dated names. Reuse or extend the scripts in `research_notes/Roomba 694 sensor exploitation ideas/data_analysis/` to analyse them.
- When a step changes the plan or replaces an estimate by a measurement, update the status tables of `notes/H_cartographie_strategie.md`.
- Commit after each completed step, with messages in the repository's style ("Roomba 694 : …", in French), and push to `claude/pensive-hopper-qmvast`. Change nothing outside `roomba694_recherche/`. No pull request unless I ask.
