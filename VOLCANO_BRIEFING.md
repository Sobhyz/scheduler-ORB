# Volcano Scheduler — Complete Briefing

---

## 1. The Problem Being Solved

Each model runs as a job that requests computing resources (GPUs, CPUs, memory, storage) for some
duration. Because the hardware is shared and finite, a scheduler must decide
which job runs first when not everything fits at once. The chosen scheduler is
Volcano, running on Kubernetes.

---

## 2. What Volcano Is

Volcano is a batch scheduler that runs on top of Kubernetes. Kubernetes by
itself manages containers but has a weak, one-at-a-time scheduler unsuited to
batch AI workloads. Volcano adds the intelligent scheduling layer: it decides
the order and placement of jobs using priority, fairness, grouping, and
backfill rules.

The system is three layers:

- **Docker** — runs a single container (one isolated program).
- **Kubernetes** — manages many containers across machines.
- **Volcano** — decides which jobs run first and where.

---

## 3. Master and Worker Nodes

A Kubernetes cluster is made of nodes (machines), of two kinds:

- **Master node (control-plane)** — the brain. It runs the Kubernetes core and
  the Volcano scheduler, and makes all scheduling decisions. By default it does
  not run user jobs.
- **Worker node** — the muscle. It runs the actual jobs (the models), taking
  orders from the master.

Volcano fully supports this multi-node arrangement: the scheduler runs on the
master and assigns jobs across the worker nodes, which is how a real production
cluster operates — the master coordinates, the workers (with the GPUs) execute.

**On this phase "the development laptop", the cluster has only one node.** It was created as
a single-node cluster, so there are no separate workers. That one node is
therefore both master and worker at once: it runs Volcano and also runs the
jobs. The tool used to build the local cluster removes the usual restriction
that prevents the master from running jobs, precisely because in a single-node
setup there is nowhere else for jobs to go. This is why the test jobs ran on the
control-plane node. In production this changes automatically: jobs run on worker
nodes, and no configuration needs to change.

---

## 4. How Scheduling Decisions Are Made

Volcano runs a cycle of stages called **actions**, applying **plugins**
(decision rules) to choose what runs. The configured actions are:

- **enqueue** — admit jobs into the competition.
- **allocate** — assign resources to jobs by priority.
- **backfill** — fit small jobs into idle gaps left while large jobs wait.
- **preempt** — allow a higher-priority job to displace a lower-priority one.

*The plugins* include priority (rank by importance, then arrival, then ID), *gang*
(all-or-nothing grouping), *drf* (fairness across resource types), *proportion*
(per-queue fair share), *binpack* (tight packing), and *sla* (anti-starvation wait
limit). *Plugins* are grouped in tiers; earlier tiers override later ones.

---

## 5. Key Concepts Explained

### Gang scheduling
A job may consist of several pods that must run together (for example, a model
needing four GPUs at once). Gang scheduling guarantees all of them start
together or none do. This prevents a deadlock where a job grabs some resources
and waits forever for the rest. This is the single most important reason Volcano
was chosen.

### DRF (Dominant Resource Fairness)
A fairness rule for when jobs request different mixes of resources (some need
more GPU, others more CPU). DRF looks at each job's largest ("dominant")
resource demand and balances those across jobs, so no single type of job
monopolizes the cluster. In practice it tends to favor jobs that request fewer
resources.

### Preemption — and an important clarification
Preemption means a higher-priority job can displace a lower-priority job that is
already running, to take its resources. **Preemption is driven by priority, not
by time.** It does not, on its own, stop a job for running too long.

The competition's requirement is different: stop only the jobs that exceed their
declared time limit, and never disturb any other job. That requirement is **not
preemption** — it is a **per-job time limit**. A job can be given a maximum
runtime, after which Kubernetes stops it automatically, independent of the
scheduler. Therefore, if the intent is that no job should ever be displaced
except those that overrun their declared time, the correct design is to
**disable preemption** (remove it from the actions and disable it on the
plugins) and instead **set a time limit on each job**. Preemption and time
limits are two separate mechanisms and should not be confused.

### Maximum waiting time (ETA) per job
A scheduler cannot promise an exact wait time, because it depends on what else
is submitted and on resource availability at that moment. However, an
**upper bound** can be enforced: the `sla-waiting-time` setting of the sla
plugin forces any job that has waited longer than that limit to proceed.
Therefore the maximum waiting time is effectively the configured
`sla-waiting-time` value (for example one hour). The typical wait is shorter and
load-dependent and cannot be calculated precisely in advance, but the SLA value
provides a guaranteed ceiling.

---

## 6. Points of Strength

- **Gang scheduling** — all-or-nothing allocation prevents multi-GPU deadlocks.
- **Multi-resource requests** — a job can ask for GPU, CPU, and memory together,
  and Volcano allocates them as a unit.
- **Priority scheduling** with deterministic tie-breaks (priority, then arrival,
  then ID(lowest first)).
- **Backfill** — small jobs fill idle gaps, improving utilization.
- **Fairness** — DRF and proportion prevent any participant from monopolizing
  resources.
- **Anti-starvation** — the sla plugin guarantees a maximum waiting time.
- **Native AI/ML support** — works with PyTorch, TensorFlow, and Ray.
- **Customizable** — behavior is set through a configuration file, and new rules
  can be added as plugins.
- **Production-ready scaling** — the same configuration runs unchanged from a
  single laptop node to a multi-node GPU cluster.

---
**Examples:**

Setup: 3 jobs arrive
Job A: priority=low,  arrived 1st, wants 1 CPU,  needs 10 min
Job B: priority=high, arrived 2nd, wants 4 CPUs, needs 2 min
Job C: priority=low,  arrived 3rd, wants 1 CPU,  needs 5 min

Only some can run at once. Who goes first?
The answer CHANGES depending on which plugins are active.

Case 1: Just the priority plugin
The priority plugin's fixed internal order: priorityClass → arrival → ID
Step 1 — compare priorityClass:
   B is high, A and C are low → B WINS, goes first

Step 2 — A and C are tied (both low) → use arrival:
   A arrived before C → A second, C third

ORDER: B → A → C
You cannot reorder these three checks. The plugin always does priority first, arrival second, ID third. That's hardcoded.

Case 2: Add the drf plugin (favors fewer resources)
Now resource size enters the decision. drf prefers jobs asking for fewer resources.
B wants 4 CPUs (large), A and C want 1 CPU each (small)

With drf influencing: the small jobs (A, C) become more attractive
because they're "cheaper" and fit easily.

ORDER might become: A → C → B
   (even though B is high priority, drf pulls the small jobs up)
Same 3 jobs, different order — just by adding a plugin. You didn't reorder "priority/arrival/ID"; you changed which rule dominates.

Case 3: Tiers decide who wins when plugins disagree
priority says "B first" (it's high). drf says "A first" (it's small). They conflict. Tiers resolve it — earlier tier wins.
CONFIG VERSION 1 — priority in the TOP tier:
tiers:
- plugins:
  - name: priority      ← tier 1 (stronger)
- plugins:
  - name: drf           ← tier 2 (weaker)

Result: priority wins the conflict → B first → ORDER: B → A → C
CONFIG VERSION 2 — drf in the TOP tier:
tiers:
- plugins:
  - name: drf           ← tier 1 (stronger)
- plugins:
  - name: priority      ← tier 2 (weaker)

Result: drf wins the conflict → small jobs first → ORDER: A → C → B
Identical jobs, identical plugins — but swapping the tier order flips the result. That's how you control behavior without ever touching the internal "priority→arrival→ID" chain.

Case 4: Your custom area rule (if you wrote the plugin)
If you wrote a custom area plugin (area = resources × time):
Job A: 1 CPU × 10 min = 10
Job B: 4 CPU × 2 min  = 8
Job C: 1 CPU × 5 min  = 5

Smallest area first → C (5) → B (8) → A (10)
ORDER: C → B → A
A completely different order again — because a custom plugin introduced a brand-new rule that doesn't exist built-in.

The Big Picture
Same 3 jobs, four different orderings:

Priority plugin only:        B → A → C   (priority rules)
+ drf added:                 A → C → B   (small jobs favored)
drf in top tier:             A → C → B   (drf wins conflicts)
priority in top tier:        B → A → C   (priority wins conflicts)
Custom area plugin:          C → B → A   (area rules)
What you CANNOT change:
   inside the priority plugin → always priority, then arrival, then ID

What you CAN change:
   - WHICH plugins are active (priority? drf? sla? custom?)
   - WHICH tier each is in (top tier wins conflicts)
   - ADD a custom plugin for entirely new rules (area, duration)
The analogy
The priority plugin = one judge with fixed rules
   (always scores priority first, then arrival, then ID — can't change them)

Your scheduler = a PANEL of judges (plugins)
   - you choose WHICH judges sit on the panel (which plugins)
   - you choose WHICH judge is head judge (tier order)
   - you can hire a NEW judge with new rules (custom plugin)

You can't change one judge's personal rulebook,
but you can change the whole panel and who leads it.

---

## 7. Cases Volcano Does Not Cover (Out of the Box)

- **Ordering by job duration or by area (resources × time).** Volcano's built-in
  plugins judge jobs by resources and priority, never by how long a job will
  run. DRF approximates the resource dimension only. The exact "smallest area
  first" rule (resources × time) requires a custom plugin implementing a job
  ordering function, written in Go and compiled into Volcano.
- **Stopping jobs that exceed their declared time.** This is handled by a per-job
  time limit, not by the scheduler.
- **Exact waiting-time prediction.** Only an upper bound (the SLA limit) can be
  guaranteed; a precise ETA cannot be computed in advance.

---

## 8. Points of Weakness / Risks

- **Operational complexity.** Volcano on Kubernetes is a real distributed system
  with a learning curve; diagnosing issues requires Kubernetes knowledge.
- **Custom rules require Go.** Any policy beyond the built-in plugins (such as
  the area-based rule) must be written and maintained as code.
- **The scheduler does not score models or enforce time limits.** Those must be
  built around it as separate components.
- **Development testing is hardware-limited.** A laptop cannot represent real
  load or real GPUs; multi-GPU behavior is only fully verifiable on the real
  cluster.
- **Tooling is Kubernetes-specific.** If the production environment provides a
  different system (such as Slurm), the concepts transfer but the tooling and
  some of the work would change.

---

## 9. What Has Been Verified

On a local single-node cluster with Volcano installed, the following behaviors
were confirmed by submitting jobs and observing the scheduler:

- **Gang scheduling (fits):** a three-pod job started all pods together and
  completed together.
- **Gang scheduling (cannot fit):** a job requesting more than the available
  resources started zero pods and remained Pending, proving all-or-nothing
  behavior.
- **Priority and preemption:** a high-priority job displaced a running
  low-priority job and took its resources; the low-priority job returned to
  Pending and resumed once resources freed.

---

## 10. Summary

Volcano is the scheduling brain that sits on Kubernetes and decides which
competing model-jobs run, in what order, and where. Its decisive strength is
gang scheduling, which safely handles multi-GPU jobs. It provides priority,
fairness, backfill, and a guaranteed maximum wait time, all through a single
configuration that scales unchanged from the test laptop to a production GPU
cluster. It does not natively order jobs by duration or area, does not by itself
stop overrunning jobs or score models, and cannot predict exact wait times;
these are addressed respectively by a custom plugin, per-job time limits, a
separate scoring pipeline, and the SLA upper bound. The recommended design point
to confirm with the team is the treatment of preemption: if the only jobs that
should ever be stopped are those exceeding their declared time, preemption
should be disabled and per-job time limits used instead.
```

